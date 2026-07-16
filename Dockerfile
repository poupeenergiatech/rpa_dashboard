# Imagem oficial do Playwright já traz Python + Chromium + todas as libs
# de SO necessárias -- evita o problema de "sem sudo" que existe rodando
# fora de container (playwright install --with-deps não funciona sem sudo).
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

# Timezone do SO: sem isso o Chromium (e o filtro "Hoje" calculado no
# front-end do site via JS Date) roda em UTC, mesmo com o TZ do Python já
# corrigido via tzdata/zoneinfo -- isso causava o filtro "Hoje" capturar só
# as últimas ~3h do dia em vez do dia inteiro (ex.: execução de 15/07 às
# 23:55 -03 = 02:55 UTC de 16/07, então o Chromium já considerava "hoje"
# como sendo 16/07). O pacote tzdata do PyPI (requirements.txt) só cobre o
# zoneinfo do Python -- aqui instalamos o tzdata do SO (apt), que traz o
# banco IANA que faltava, para todo o resto do container (Chromium incluso).
ENV TZ=America/Sao_Paulo
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rpa_dashboard.py scheduler.py ./

CMD ["python3", "scheduler.py"]
