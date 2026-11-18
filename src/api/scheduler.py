from contextlib import contextmanager
import logging
import os
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from src.services.repet import sync_repet_data
from src.database.connection import get_db

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = AsyncIOScheduler()

_REPET_LOCK_ID = 74839202
_REPET_LOCK_FILE = Path("data/.repet_sync.lock")


@contextmanager
def advisory_file_lock(lock_path: Path, blocking: bool = True):
    """Cross-process file lock helper supporting POSIX (fcntl) and Windows (msvcrt)."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    acquired = False
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        os.lseek(fd, 0, os.SEEK_SET)
        if os.name == "nt":
            import msvcrt

            if blocking:
                for _ in range(6):
                    try:
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                        acquired = True
                        break
                    except OSError:
                        continue
            else:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    acquired = True
                except OSError:
                    acquired = False
        else:
            import fcntl

            flags = fcntl.LOCK_EX if blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                fcntl.flock(fd, flags)
                acquired = True
            except OSError:
                acquired = False
        yield acquired
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)


@contextmanager
def _try_repet_cron_lock(db):
    """Intenta adquirir un lock exclusivo no bloqueante para evitar ejecuciones simultáneas entre workers."""
    bind_engine = db.get_bind()
    if bind_engine is not None and bind_engine.dialect.name == "postgresql":
        acquired = bool(db.execute(text(f"SELECT pg_try_advisory_lock({_REPET_LOCK_ID})")).scalar())
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    db.execute(text(f"SELECT pg_advisory_unlock({_REPET_LOCK_ID})"))
                except Exception:
                    db.rollback()
                    db.execute(text(f"SELECT pg_advisory_unlock({_REPET_LOCK_ID})"))
        return

    with advisory_file_lock(_REPET_LOCK_FILE, blocking=False) as acquired:
        yield acquired


async def job_sync_repet():
    """Job wrapper para inyectar la sesión de DB con exclusión mutua entre workers."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        with _try_repet_cron_lock(db) as acquired:
            if not acquired:
                logger.info("Sincronización RePET omitida: otro worker ya posee el lock.")
                return
            logger.info("Ejecutando Job Cron: Sincronización RePET...")
            await sync_repet_data(db)
    finally:
        db.close()


def start_scheduler():
    """Inicializa el cron job de forma idempotente."""
    # Ejecutar todos los días a las 03:00 AM
    scheduler.add_job(job_sync_repet, 'cron', hour=3, minute=0, id='sync_repet_daily', replace_existing=True)
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler de tareas en segundo plano iniciado (RePET cron job programado).")


def stop_scheduler():
    """Detiene el cron job de forma segura."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido.")
