"""
Servidor local só para teste: simula /api/webhooks/scans do
vendedores-dashboard-allpfit, valida o header Authorization (Bearer) e loga o
payload recebido. Não usar em produção — é apenas para validar o envio do
RPA localmente antes de apontar para a URL real.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)
EXPECTED_SECRET = os.environ["SCANS_WEBHOOK_SECRET"]


@app.post("/api/webhooks/scans")
def receive_scans():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {EXPECTED_SECRET}":
        return jsonify({"error": "invalid secret"}), 401

    payload = request.get_json(force=True)
    print("=== payload recebido ===")
    print(payload)
    return jsonify({"status": "ok", "received": payload}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8787)
