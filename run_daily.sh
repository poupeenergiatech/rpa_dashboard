#!/bin/bash
# Wrapper para rodar o RPA diariamente via cron, com log por dia.
set -euo pipefail

cd /home/poupe/rpa_qrcode
mkdir -p logs

source .venv/bin/activate
python3 rpa_dashboard.py >> "logs/rpa_$(date +%F).log" 2>&1
