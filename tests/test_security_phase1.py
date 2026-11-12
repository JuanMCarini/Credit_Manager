import sys
from pathlib import Path
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.config import APIConfig
from src.api.dependencies.auth import enforce_rbac, admin_only
from src.api.routes.system import download_uploaded_file, UPLOADS_BASE_DIR
from src.database.models.auth import Usuario, Rol, TipoRolEnum
from scripts.reset_and_seed_db import _verify_safe_dev_environment


def _make_request(method: str, path: str, token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def _run_coro_sync(coro):
    """Ejecuta una corrutina sin awaits bloqueantes de I/O sin instanciar socketpair."""
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value


def _create_user_with_role(db_session, email: str, rol_enum: TipoRolEnum) -> Usuario:
    rol = db_session.query(Rol).filter(Rol.nombre == rol_enum).first()
    if not rol:
        rol = Rol(nombre=rol_enum)
        db_session.add(rol)
        db_session.flush()
    user = Usuario(
        email=email,
        hashed_password="hashed_password_placeholder",
        nombre_completo=f"User {rol_enum.name}",
        rol_id=rol.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_task_1_1_rejects_short_or_default_secret_key():
    with pytest.raises(ValueError):
        APIConfig(env="production", API_SECRET_KEY="short_key")

    with pytest.raises(ValueError):
        APIConfig(
            env="production",
            API_SECRET_KEY="super_secret_key_change_in_production",
        )

    valid_cfg = APIConfig(
        env="production",
        API_SECRET_KEY="a_very_strong_production_secret_key_over_32_chars",
    )
    assert len(valid_cfg.secret_key) >= 32


def test_task_1_2_blocks_path_traversal_in_uploads(db_session):
    admin = _create_user_with_role(db_session, "admin_sec@test.com", TipoRolEnum.ADMINISTRADOR)

    # Categoría no permitida
    with pytest.raises(HTTPException) as exc_cat:
        download_uploaded_file(categoria=" Hack ", filename="doc.pdf", current_user=admin)
    assert exc_cat.value.status_code == 400

    # Intento de Path Traversal con ../
    with pytest.raises(HTTPException) as exc_trav:
        download_uploaded_file(categoria="legajos", filename="../../.env", current_user=admin)
    assert exc_trav.value.status_code in (400, 403, 404)

    # Archivo válido dentro de data/uploads/legajos
    legajos_dir = UPLOADS_BASE_DIR / "legajos"
    legajos_dir.mkdir(parents=True, exist_ok=True)
    sample_file = legajos_dir / "test_sec_phase1.txt"
    sample_file.write_text("ok", encoding="utf-8")
    try:
        resp = download_uploaded_file(
            categoria="legajos",
            filename="test_sec_phase1.txt",
            current_user=admin,
        )
        assert Path(resp.path).resolve() == sample_file.resolve()
    finally:
        sample_file.unlink(missing_ok=True)


def test_task_1_3_rbac_enforces_read_and_write_permissions(db_session):
    from src.api.dependencies.auth import create_access_token

    cobranzas_user = _create_user_with_role(
        db_session, "cobranzas@test.com", TipoRolEnum.OPERADOR_COBRANZAS
    )
    oficial_user = _create_user_with_role(
        db_session, "oficial@test.com", TipoRolEnum.OFICIAL_CREDITO
    )
    admin_user = _create_user_with_role(
        db_session, "admin_rbac@test.com", TipoRolEnum.ADMINISTRADOR
    )

    cob_token = create_access_token({"sub": cobranzas_user.email})
    ofi_token = create_access_token({"sub": oficial_user.email})
    adm_token = create_access_token({"sub": admin_user.email})

    # Sin token en ruta privada -> 401
    with pytest.raises(HTTPException) as exc_unauth:
        _run_coro_sync(enforce_rbac(_make_request("GET", "/api/v1/clientes"), db=db_session))
    assert exc_unauth.value.status_code == 401

    # OPERADOR_COBRANZAS y OFICIAL_CREDITO bloqueados (403) en GET de módulos restringidos
    restricted_paths = [
        "/api/v1/inversores",
        "/api/finanzas/bancos",
        "/api/finanzas/posicion-iva",
        "/api/finanzas/posicion-iibb",
        "/api/v1/bcra/export",
        "/api/v1/system/modules",
    ]
    for restricted in restricted_paths:
        for tok in (cob_token, ofi_token):
            with pytest.raises(HTTPException) as exc_forbidden:
                _run_coro_sync(
                    enforce_rbac(_make_request("GET", restricted, tok), db=db_session)
                )
            assert exc_forbidden.value.status_code == 403

    # OPERADOR_COBRANZAS y OFICIAL_CREDITO pueden consultar auxiliares y clientes
    for tok in (cob_token, ofi_token):
        res_cli = _run_coro_sync(
            enforce_rbac(_make_request("GET", "/api/v1/clientes", tok), db=db_session)
        )
        assert res_cli is not None
        res_aux = _run_coro_sync(
            enforce_rbac(
                _make_request("POST", "/api/v1/auxiliares/provincias/data", tok),
                db=db_session,
            )
        )
        assert res_aux is not None

    # admin_only bloquea roles no administradores
    with pytest.raises(HTTPException) as exc_adm:
        admin_only(current_user=oficial_user)
    assert exc_adm.value.status_code == 403
    assert admin_only(current_user=admin_user) == admin_user

    # ADMINISTRADOR tiene acceso a rutas restringidas
    assert (
        _run_coro_sync(
            enforce_rbac(_make_request("GET", "/api/v1/inversores", adm_token), db=db_session)
        )
        == admin_user
    )


def test_task_1_4_reset_and_seed_db_guard(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setattr(sys, "argv", ["reset_and_seed_db.py", "--force-destroy-dev"])
    with pytest.raises(SystemExit) as exc_prod:
        _verify_safe_dev_environment()
    assert exc_prod.value.code == 1

    monkeypatch.setenv("ENV", "development")
    monkeypatch.setattr(sys, "argv", ["reset_and_seed_db.py"])
    with pytest.raises(SystemExit) as exc_no_flag:
        _verify_safe_dev_environment()
    assert exc_no_flag.value.code == 1

    monkeypatch.setenv("ENV", "development")
    monkeypatch.setattr(sys, "argv", ["reset_and_seed_db.py", "--force-destroy-dev"])
    _verify_safe_dev_environment()

