# Imagem oficial do Playwright já traz Python + Chromium + todas as libs
# de SO necessárias -- evita o problema de "sem sudo" que existe rodando
# fora de container (playwright install --with-deps não funciona sem sudo).
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rpa_dashboard.py scheduler.py ./

CMD ["python3", "scheduler.py"]
