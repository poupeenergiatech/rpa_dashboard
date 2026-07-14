"""
Entrypoint de produção (Easypanel): processo de longa duração que roda o
RPA (rpa_dashboard.run) todo dia às 23:55 (America/Sao_Paulo).

Uma falha em uma execução (ex: webhook fora do ar) é logada mas não
derruba o processo -- o scheduler continua de pé para tentar de novo no
dia seguinte.
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


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(job, CronTrigger(hour=23, minute=55))
    logger.info(
        "Scheduler iniciado — RPA agendado para todo dia às 23:55 (America/Sao_Paulo)"
    )
    scheduler.start()
