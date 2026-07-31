"""
Entrypoint de produção (Easypanel): processo de longa duração que roda o
RPA (rpa_dashboard.run) três vezes por dia -- 12:00, 18:00 e 23:55
(America/Sao_Paulo) -- para dar checkpoints intermediários do dia além do
fechamento final. Cada execução lê o total acumulado do dia via filtro
"Hoje" e o webhook faz upsert por (academia_id, data), então os envios
apenas sobrescrevem o total com o valor mais recente -- não há risco de
somar em duplicidade entre as três execuções.

Uma falha em uma execução (ex: webhook fora do ar) é logada mas não
derruba o processo -- o scheduler continua de pé para tentar de novo no
próximo horário.
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from rpa_dashboard import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("scheduler")


def job():
    logger.info("Iniciando execução diária do RPA")
    try:
        run()
        logger.info("Execução concluída com sucesso")
    except Exception:
        logger.exception("Execução do RPA falhou")


TZ = "America/Sao_Paulo"

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=TZ)
    # timezone precisa ser passado explicitamente ao CronTrigger também:
    # sem system tzdata configurado no container (Easypanel), o CronTrigger
    # tenta detectar o fuso local via tzlocal e cai silenciosamente em UTC,
    # ignorando o timezone do BlockingScheduler.
    scheduler.add_job(job, CronTrigger(hour=12, minute=0, timezone=TZ))
    scheduler.add_job(job, CronTrigger(hour=18, minute=0, timezone=TZ))
    scheduler.add_job(job, CronTrigger(hour=23, minute=55, timezone=TZ))
    logger.info(
        "Scheduler iniciado — RPA agendado para todo dia às 12:00, 18:00 e 23:55 (America/Sao_Paulo)"
    )
    scheduler.start()
