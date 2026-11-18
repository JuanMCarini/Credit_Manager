from pathlib import Path

from src.database import connection
from src.database.models import Provincia, Banco, Concepto
from src.database.models.auth import Rol, TipoRolEnum, Usuario
from src.database.models.system import ModuloSistema
from src.database.seed_admin import seed_admin
from src.database.seed_bancos import BANCOS_ARGENTINA, seed_bancos
from src.database.seed_conceptos import seed_conceptos
from src.database.seed_geography import seed_provincias
from src.database.seed_modulos import DEFAULT_MODULOS, seed_modulos


class _NonClosingSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def _run_coro_sync(coro):
    """Ejecuta corrutinas sin levantar ProactorEventLoop/socketpair en el sandbox Windows."""
    try:
        while True:
            coro.send(None)
    except StopIteration as stop:
        return stop.value


def test_seeds_idempotency_no_duplicates(db_session):
    seed_bancos(db_session)
    seed_bancos(db_session)
    assert db_session.query(Banco).count() == len(BANCOS_ARGENTINA)

    seed_provincias(db_session)
    count_prov = db_session.query(Provincia).count()
    assert count_prov > 0
    seed_provincias(db_session)
    assert db_session.query(Provincia).count() == count_prov

    seed_conceptos(db_session)
    count_conc = db_session.query(Concepto).count()
    assert count_conc > 0
    seed_conceptos(db_session)
    assert db_session.query(Concepto).count() == count_conc

    seed_modulos(db_session)
    seed_modulos(db_session)
    assert db_session.query(ModuloSistema).count() == len(DEFAULT_MODULOS)

    seed_admin(db_session)
    seed_admin(db_session)
    assert db_session.query(Rol).count() == len(TipoRolEnum)
    assert db_session.query(Usuario).count() == 1


def test_scheduler_lock_skips_concurrent_worker_and_safe_start_stop(
    db_session, tmp_path, monkeypatch
):
    from src.api import scheduler as sched_mod

    lock_file = tmp_path / ".repet_sync.lock"
    calls = []

    async def _fake_sync(_db):
        calls.append(1)

    monkeypatch.setattr(sched_mod, "_REPET_LOCK_FILE", lock_file)
    monkeypatch.setattr(sched_mod, "get_db", lambda: iter([_NonClosingSessionProxy(db_session)]))
    monkeypatch.setattr(sched_mod, "sync_repet_data", _fake_sync)

    # Sin contención: el cron ejecuta sync_repet_data una vez
    _run_coro_sync(sched_mod.job_sync_repet())
    assert len(calls) == 1

    # Con el lock tomado por otro proceso/worker: debe omitirse la ejecución
    with sched_mod.advisory_file_lock(lock_file, blocking=False) as outer_locked:
        assert outer_locked is True
        _run_coro_sync(sched_mod.job_sync_repet())
    assert len(calls) == 1

    # stop_scheduler cuando no está corriendo no debe lanzar excepción
    if not sched_mod.scheduler.running:
        sched_mod.stop_scheduler()


def test_engine_pool_and_dockerfile_gunicorn_timeout():
    repo_root = Path(__file__).resolve().parent.parent
    dockerfile = (repo_root / "Dockerfile.backend").read_text(encoding="utf-8")

    assert connection.engine.pool._recycle == 1800
    assert connection.engine.pool._pre_ping is True
    assert '"--timeout", "600"' in dockerfile
    assert '"--graceful-timeout", "30"' in dockerfile
