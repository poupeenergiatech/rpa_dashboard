"""
RPA - ALLP FIT QR Code Manager (https://qrcode.allpfit.com.br/)

Faz login, seleciona o filtro de período "Hoje" e a campanha "Alle Energia"
no Dashboard, extrai:
  - Cliques (Hoje): número total exibido no card
  - Cliques por Origem: número de cliques de hoje (campanha Alle Energia),
    agrupados por unidade/academia

e envia esses dois números como payload para o webhook
vendedores-dashboard-allpfit (/api/webhooks/scans).

O card "Cliques por Origem" é um gráfico de pizza (Recharts) sem rótulos em
texto simples, então os números por origem são calculados localmente a
partir das respostas REST do Supabase interceptadas durante a navegação
(join de qr_clicks x qr_codes, filtrando por campaigns.name e agrupando por
units.name), em vez de tentar ler o SVG do gráfico.
"""

import json
import os
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

URL = "https://qrcode.allpfit.com.br/"
CAMPAIGN_NAME = "Alle Energia"
PERIOD_LABEL = "Hoje"
TZ = ZoneInfo("America/Sao_Paulo")

EMAIL = os.environ["ALLPFIT_EMAIL"]
PASSWORD = os.environ["ALLPFIT_PASSWORD"]
WEBHOOK_URL = os.environ["SCANS_WEBHOOK_URL"]
WEBHOOK_SECRET = os.environ["SCANS_WEBHOOK_SECRET"]


def run():
    qr_codes_by_id = {}
    today_clicks = []
    state = {"current_gte": None}

    def on_response(response):
        url = response.url
        if "supabase.co" not in url or "/rest/v1/" not in url:
            return
        if "/rest/v1/qr_codes" in url:
            try:
                rows = response.json()
            except Exception:
                return
            for row in rows:
                qr_codes_by_id[row["id"]] = row
        elif "/rest/v1/qr_clicks" in url:
            qs = parse_qs(urlparse(url).query)
            gte_param = qs.get("clicked_at", [""])[0]  # e.g. "gte.2026-07-14T03:00:00.000Z"
            if not gte_param.startswith("gte."):
                return
            gte_value = gte_param[len("gte."):]
            try:
                rows = response.json()
            except Exception:
                return

            # Só nos interessam os cliques do range de data mais recente
            # (o filtro "Hoje" ativo). Ranges mais antigos (ex: fetch
            # residual de "30 dias" ainda em voo) são descartados.
            if state["current_gte"] is None or gte_value > state["current_gte"]:
                state["current_gte"] = gte_value
                today_clicks.clear()
                today_clicks.extend(rows)
            elif gte_value == state["current_gte"]:
                today_clicks.extend(rows)
            # gte_value < current_gte -> resposta de range antigo, ignora

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(20000)
        page.on("response", on_response)

        # 1. Login
        page.goto(URL, wait_until="networkidle")
        page.fill("#email", EMAIL)
        page.fill("#password", PASSWORD)
        page.click("text=Entrar")
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1500)

        # 2. Filtro de período -> "Hoje"
        page.get_by_role("combobox").nth(0).click(force=True)
        page.wait_for_timeout(500)
        page.get_by_role("option", name=PERIOD_LABEL, exact=True).click()
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1000)

        # 3. Filtro de campanha -> "Alle Energia"
        page.get_by_role("combobox").nth(1).click(force=True)
        page.wait_for_timeout(500)
        page.get_by_role("option", name=CAMPAIGN_NAME, exact=True).click()
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1500)

        # 4. Ler o card "Cliques (Hoje)" diretamente do DOM (conferência
        # cruzada com o valor calculado via join, abaixo)
        card = page.locator("text=Cliques (Hoje)").locator(
            "xpath=ancestor::*[contains(@class,'rounded')][1]"
        )
        cliques_hoje_text = card.first.inner_text()
        cliques_hoje_card = None
        for line in cliques_hoje_text.splitlines():
            line = line.strip()
            if line.replace(".", "").isdigit():
                cliques_hoje_card = int(line.replace(".", ""))

        page.screenshot(
            path="/home/poupe/rpa_qrcode/dashboard_hoje_alle_energia.png",
            full_page=True,
        )

        browser.close()

    # 5. Join local: qr_clicks (hoje) x qr_codes, filtrando por campanha
    campaign_qr_ids = {
        qr_id
        for qr_id, row in qr_codes_by_id.items()
        if (row.get("campaigns") or {}).get("name") == CAMPAIGN_NAME
    }

    origem_counter = Counter()
    clique_ids_vistos = set()
    for click in today_clicks:
        cid = click["id"]
        if cid in clique_ids_vistos:
            continue
        clique_ids_vistos.add(cid)
        qr_id = click["qr_id"]
        if qr_id not in campaign_qr_ids:
            continue
        qr_row = qr_codes_by_id.get(qr_id, {})
        unit_name = (qr_row.get("units") or {}).get("name", "Origem desconhecida")
        origem_counter[unit_name] += 1

    total_campanha_hoje = sum(origem_counter.values())
    if cliques_hoje_card is not None and cliques_hoje_card != total_campanha_hoje:
        raise RuntimeError(
            f"Divergência entre o card 'Cliques (Hoje)' ({cliques_hoje_card}) "
            f"e o total calculado via join ({total_campanha_hoje}) — "
            "não enviando payload até isso ser investigado."
        )

    now = datetime.now(TZ)
    payload = {
        "data": now.strftime("%d/%m/%Y"),
        "gerado_em": now.strftime("%d/%m/%Y %H:%M"),
        "por_academia": [
            {"academia": academia, "total_scans": total}
            for academia, total in sorted(
                origem_counter.items(), key=lambda kv: -kv[1]
            )
        ],
    }

    print("Payload:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        timeout=15,
    )
    print(f"POST {WEBHOOK_URL} -> {response.status_code}")
    print(response.text[:500])
    response.raise_for_status()

    return payload


if __name__ == "__main__":
    run()
