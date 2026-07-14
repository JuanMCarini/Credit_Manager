from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.repet import sync_repet_data
from src.database.connection import get_db
import logging

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = AsyncIOScheduler()

async def job_sync_repet():
    """Job wrapper para inyectar la sesión de DB."""
    logger.info("Ejecutando Job Cron: Sincronización RePET...")
    db_gen = get_db()
    db = next(db_gen)
    try:
        await sync_repet_data(db)
    finally:
        db.close()

def start_scheduler():
    """Inicializa el cron job."""
    # Ejecutar todos los días a las 03:00 AM
    scheduler.add_job(job_sync_repet, 'cron', hour=3, minute=0, id='sync_repet_daily', replace_existing=True)
    scheduler.start()
    logger.info("Scheduler de tareas en segundo plano iniciado (RePET cron job programado).")

def stop_scheduler():
    """Detiene el cron job."""
    scheduler.shutdown()
    logger.info("Scheduler detenido.")
