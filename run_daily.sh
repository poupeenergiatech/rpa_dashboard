#!/bin/bash
# Wrapper para rodar o RPA manualmente/localmente com log por dia.
# Em produção o agendamento é feito pelo scheduler.py rodando dentro do
# container no Easypanel -- este script não é mais chamado por cron aqui.
set -euo pipefail

cd /home/poupe/rpa_qrcode
mkdir -p logs

source .venv/bin/activate
python3 rpa_dashboard.py >> "logs/rpa_$(date +%F).log" 2>&1
