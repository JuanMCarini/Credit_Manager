import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import pytest

from src.database.models import (
    Cliente,
    Credito,
    EstadoClienteEnum,
    EstadoCredito,
    HistorialEstadoCliente,
    HistorialEstadoCredito,
    Rol,
    TipoRolEnum,
    Usuario,
)
from src.database.models.auth import RegistroAuditoria
from src.api.dependencies.auth import (
    create_access_token,
    enforce_rbac,
    extract_client_ip,
    sanitize_audit_payload,
    _resolve_audit_entity,
    _resolve_sensitive_read_action,
)


def _run_coro_sync(coro):
    """Ejecuta una corrutina sin depender de socketpair de asyncio en Windows."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def _make_fake_request(
    method: str,
    path: str,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    json_body: dict | None = None,
    query_params: dict[str, str] | None = None,
    client_host: str = "10.0.0.5",
):
    raw_headers = {k.lower(): v for k, v in (headers or {}).items()}
    if token:
        raw_headers["authorization"] = f"Bearer {token}"
    if json_body is not None:
        raw_headers.setdefault("content-type", "application/json")

    class _Headers:
        def get(self, key: str, default=None):
            return raw_headers.get(key.lower(), default)

    async def _json():
        if json_body is None:
            raise ValueError("No JSON body")
        return json_body

    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
        headers=_Headers(),
        cookies={},
        query_params=query_params or {},
        client=SimpleNamespace(host=client_host),
        json=_json,
    )


@pytest.fixture
def admin_user(db_session):
    rol = db_session.query(Rol).filter(Rol.nombre == TipoRolEnum.ADMINISTRADOR).first()
    if not rol:
        rol = Rol(nombre=TipoRolEnum.ADMINISTRADOR, descripcion="Admin")
        db_session.add(rol)
        db_session.flush()
    user = db_session.query(Usuario).filter(Usuario.email == "admin_p3@creditmanager.com").first()
    if not user:
        user = Usuario(
            email="admin_p3@creditmanager.com",
            hashed_password="hash",
            nombre_completo="Admin Phase 3",
            is_active=True,
            rol_id=rol.id,
        )
        db_session.add(user)
        db_session.commit()
    return user


# =====================================================================
# TAREA 3.1: Inmutabilidad Append-Only de Tablas de Auditoría e Historial
# =====================================================================

def test_registro_auditoria_is_append_only(db_session, admin_user):
    log = RegistroAuditoria(
        usuario_id=admin_user.id,
        accion="Crear Liquidación (ID: 10)",
        endpoint="/api/v1/liquidaciones",
        metodo="POST",
        direccion_ip="192.168.1.25",
        estado="Éxito",
    )
    db_session.add(log)
    db_session.commit()

    # Intento de UPDATE debe fallar
    log.accion = "Acción Adulterada"
    with pytest.raises(ValueError, match="inmutables"):
        db_session.commit()
    db_session.rollback()

    # Intento de DELETE debe fallar
    persisted_log = db_session.query(RegistroAuditoria).filter_by(id=log.id).first()
    assert persisted_log is not None
    db_session.delete(persisted_log)
    with pytest.raises(ValueError, match="inmutables"):
        db_session.commit()
    db_session.rollback()


def test_historial_estados_credito_and_cliente_are_append_only(db_session, admin_user):
    cliente = Cliente(
        cuil="20334455667",
        documento="33445566",
        apellido="Inmutable",
        nombre="Cliente",
        estado=EstadoClienteEnum.ACTIVO,
    )
    db_session.add(cliente)
    db_session.flush()

    credito = Credito(
        cliente_cuil=cliente.cuil,
        capital=100000.0,
        tna_c_iva=0.50,
        plazo=12,
        fecha_emision=date(2026, 1, 15),
        estado=EstadoCredito.APROBADO,
        dia_vencimiento=10,
    )
    db_session.add(credito)
    db_session.flush()

    hist_cli = HistorialEstadoCliente(
        cliente_cuil=cliente.cuil,
        estado_anterior=None,
        estado_nuevo="ACTIVO",
        usuario_id=admin_user.id,
        origen="ALTA",
        motivo="Alta inicial",
    )
    hist_cred = HistorialEstadoCredito(
        credito_id=credito.id,
        estado_anterior=None,
        estado_nuevo="APROBADO",
        usuario_id=admin_user.id,
        origen="ORIGINACION",
        motivo="Originación inicial",
    )
    db_session.add_all([hist_cli, hist_cred])
    db_session.commit()

    # Intento de UPDATE en HistorialEstadoCliente
    hist_cli.estado_nuevo = "MOROSO"
    with pytest.raises(ValueError, match="inmutables"):
        db_session.commit()
    db_session.rollback()

    # Intento de DELETE en HistorialEstadoCredito
    persisted_cred_hist = db_session.query(HistorialEstadoCredito).filter_by(id=hist_cred.id).first()
    db_session.delete(persisted_cred_hist)
    with pytest.raises(ValueError, match="inmutables"):
        db_session.commit()
    db_session.rollback()


# =====================================================================
# TAREA 3.2: Clasificación de Dominios Financieros, IP Real y Sanitización
# =====================================================================

def test_financial_entity_classification_and_sanitization(db_session, admin_user):
    assert _resolve_audit_entity("/api/v1/liquidaciones/55") == "Liquidación"
    assert _resolve_audit_entity("/api/v1/carteras/12") == "Cartera"
    assert _resolve_audit_entity("/api/v1/inversores/series") == "Inversor / Deuda"
    assert _resolve_audit_entity("/api/cheques/99") == "Cheque"
    assert _resolve_audit_entity("/api/finanzas/bancos") == "Finanzas / Bancos"
    assert _resolve_audit_entity("/api/finanzas/comprobantes") == "Comprobante / Proveedor"
    assert _resolve_audit_entity("/api/finanzas/posicion-iva") == "Posición IVA / IIBB"
    assert _resolve_audit_entity("/api/v1/facturacion") == "Facturación"
    assert _resolve_audit_entity("/api/v1/planes") == "Plan Financiero"
    assert _resolve_audit_entity("/api/v1/system/config") == "Configuración del Sistema"

    raw_payload = {
        "id": 77,
        "monto": 250000.0,
        "password": "my_Plain_Password_123!",
        "api_secret_key": "top_secret",
        "nested": {"access_token": "jwt_token_val", "concepto": "Liquidación"},
    }
    sanitized = sanitize_audit_payload(raw_payload)
    assert sanitized["id"] == 77
    assert sanitized["monto"] == 250000.0
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["api_secret_key"] == "***REDACTED***"
    assert sanitized["nested"]["access_token"] == "***REDACTED***"
    assert sanitized["nested"]["concepto"] == "Liquidación"

    token = create_access_token({"sub": admin_user.email})
    req = _make_fake_request(
        method="POST",
        path="/api/v1/liquidaciones",
        token=token,
        headers={"X-Forwarded-For": "203.0.113.42, 10.0.0.1"},
        json_body=raw_payload,
    )
    _run_coro_sync(enforce_rbac(req, db=db_session))

    audit_entry = (
        db_session.query(RegistroAuditoria)
        .filter(RegistroAuditoria.endpoint == "/api/v1/liquidaciones")
        .order_by(RegistroAuditoria.id.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.accion == "Crear Liquidación (ID: 77)"
    assert audit_entry.direccion_ip == "203.0.113.42"
    assert audit_entry.detalles["password"] == "***REDACTED***"
    assert audit_entry.detalles["monto"] == 250000.0


# =====================================================================
# TAREA 3.3: Auditoría de Exportaciones Masivas de PII y Descargas
# =====================================================================

def test_sensitive_pii_exports_and_downloads_are_audited(db_session, admin_user):
    token = create_access_token({"sub": admin_user.email})

    # 1. Exportación regulatoria BCRA (GET)
    req_bcra = _make_fake_request(
        method="GET",
        path="/api/v1/bcra/export-excel",
        token=token,
        headers={"X-Forwarded-For": "198.51.100.88"},
        query_params={"periodo": "202605"},
    )
    _run_coro_sync(enforce_rbac(req_bcra, db=db_session))

    bcra_log = (
        db_session.query(RegistroAuditoria)
        .filter(RegistroAuditoria.endpoint == "/api/v1/bcra/export-excel")
        .order_by(RegistroAuditoria.id.desc())
        .first()
    )
    assert bcra_log is not None
    assert bcra_log.accion == "Exportación Masiva BCRA"
    assert bcra_log.metodo == "GET"
    assert bcra_log.direccion_ip == "198.51.100.88"
    assert bcra_log.detalles == {"periodo": "202605"}

    # 1b. Rutas reales Excel de BCRA (/api/v1/bcra/excel) y Saldos (/api/v1/reports/balances/excel)
    req_bcra_xlsx = _make_fake_request(
        method="GET",
        path="/api/v1/bcra/excel",
        token=token,
        headers={"X-Real-IP": "198.51.100.77"},
    )
    _run_coro_sync(enforce_rbac(req_bcra_xlsx, db=db_session))
    bcra_xlsx_log = (
        db_session.query(RegistroAuditoria)
        .filter(RegistroAuditoria.endpoint == "/api/v1/bcra/excel")
        .order_by(RegistroAuditoria.id.desc())
        .first()
    )
    assert bcra_xlsx_log is not None
    assert bcra_xlsx_log.accion == "Exportación Masiva BCRA"
    assert bcra_xlsx_log.direccion_ip == "198.51.100.77"

    req_bal_xlsx = _make_fake_request(
        method="GET",
        path="/api/v1/reports/balances/excel",
        token=token,
        headers={"X-Real-IP": "198.51.100.78"},
    )
    _run_coro_sync(enforce_rbac(req_bal_xlsx, db=db_session))
    bal_xlsx_log = (
        db_session.query(RegistroAuditoria)
        .filter(RegistroAuditoria.endpoint == "/api/v1/reports/balances/excel")
        .order_by(RegistroAuditoria.id.desc())
        .first()
    )
    assert bal_xlsx_log is not None
    assert bal_xlsx_log.accion == "Exportación Masiva de Saldos"
    assert bal_xlsx_log.direccion_ip == "198.51.100.78"

    # 2. Descarga de legajo confidencial (GET)
    req_doc = _make_fake_request(
        method="GET",
        path="/api/v1/uploads/legajos/pagare_firmado.pdf",
        token=token,
        headers={"X-Real-IP": "198.51.100.99"},
    )
    _run_coro_sync(enforce_rbac(req_doc, db=db_session))

    doc_log = (
        db_session.query(RegistroAuditoria)
        .filter(RegistroAuditoria.endpoint == "/api/v1/uploads/legajos/pagare_firmado.pdf")
        .order_by(RegistroAuditoria.id.desc())
        .first()
    )
    assert doc_log is not None
    assert "Descarga de Documento" in doc_log.accion
    assert doc_log.direccion_ip == "198.51.100.99"

    # 3. Lectura normal (GET /api/v1/clientes) NO debe saturar la tabla de auditoría
    count_before = db_session.query(RegistroAuditoria).count()
    req_normal = _make_fake_request(
        method="GET",
        path="/api/v1/clientes",
        token=token,
    )
    _run_coro_sync(enforce_rbac(req_normal, db=db_session))
    count_after = db_session.query(RegistroAuditoria).count()
    assert count_after == count_before


# =====================================================================
# TAREAS 4.1 - 4.4: Hardening de Infraestructura, Cabeceras y Dependencias
# =====================================================================

def test_phase4_infrastructure_and_security_headers():
    repo_root = Path(__file__).resolve().parent.parent

    # 4.1 Dockerfile.backend usuario no-root appuser
    dockerfile = (repo_root / "Dockerfile.backend").read_text(encoding="utf-8")
    assert "useradd" in dockerfile and "appuser" in dockerfile
    assert "USER appuser" in dockerfile

    # 4.2 docker-compose.yml bind a 127.0.0.1, healthcheck y no-new-privileges
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    assert '127.0.0.1:${HOST_PORT_DB:-5432}:5432' in compose
    assert '127.0.0.1:${HOST_PORT_BACKEND:-8000}:8000' in compose
    assert "no-new-privileges:true" in compose
    assert "pg_isready" in compose

    # 4.3 frontend/nginx.conf y middleware FastAPI
    nginx_conf = (repo_root / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "server_tokens off;" in nginx_conf
    assert "Strict-Transport-Security" in nginx_conf
    assert "Permissions-Policy" in nginx_conf
    assert "Content-Security-Policy" in nginx_conf

    from src.api.main import add_security_headers
    from fastapi.responses import JSONResponse

    async def _dummy_next(_req):
        return JSONResponse({"ok": True})

    fake_api_req = SimpleNamespace(url=SimpleNamespace(path="/api/v1/health"))
    resp = _run_coro_sync(add_security_headers(fake_api_req, _dummy_next))
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers.get("Permissions-Policy", "")
    assert resp.headers.get("Cache-Control") == "no-store"

    # 4.4 requirements.txt todas las dependencias fijadas con ==
    requirements_lines = [
        line.strip()
        for line in (repo_root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    unpinned = [line for line in requirements_lines if "==" not in line]
    assert unpinned == [], f"Dependencias sin fijar versión en requirements.txt: {unpinned}"


def test_login_client_ip_and_company_cuit_validation(db_session, tmp_path, monkeypatch):
    from fastapi import HTTPException
    from pydantic import ValidationError
    from src.api.routes.auth import _get_client_ip
    from src.api.routes.system import CompanyUpdateSchema, update_company_info
    from src.database.models.socios import SocioComercial
    import src.config as config_mod

    # 1. _get_client_ip usa X-Real-IP si X-Forwarded-For viene vacío o con separador inicial
    req_real_ip = _make_fake_request(
        method="POST",
        path="/api/auth/login",
        headers={"X-Forwarded-For": " , 10.0.0.1", "X-Real-IP": "198.51.100.55"},
        client_host="127.0.0.1",
    )
    assert _get_client_ip(req_real_ip) == "198.51.100.55"
    assert _get_client_ip(None) == "unknown"

    # 2. CompanyUpdateSchema limpia guiones en CUIT/CBU y rechaza CUITs inválidos
    with pytest.raises(ValidationError):
        CompanyUpdateSchema(razon_social="Empresa Test SA", cuit="12345")

    schema_ok = CompanyUpdateSchema(
        razon_social="Empresa Test SA",
        cuit="30-71234567-8",
        cbu="07200007-20000000123456",
    )
    assert schema_ok.cuit == "30712345678"
    assert schema_ok.cbu == "0720000720000000123456"

    # 3. update_company_info actualiza SocioComercial sin DataError y maneja colisiones como HTTP 400
    fake_env = tmp_path / ".env"
    fake_env.write_text('COMPANY_RAZON_SOCIAL="Old"\nCOMPANY_CUIT=30000000000\n', encoding="utf-8")
    monkeypatch.setattr(config_mod, "ENV_PATH", str(fake_env))
    orig_cuit = config_mod.COMPANY_DATA.cuit
    orig_rs = config_mod.COMPANY_DATA.razon_social
    try:
        socio = SocioComercial(razon_social="Original SA", cuit="30999888776")
        other = SocioComercial(razon_social="Otra SA", cuit="30111222334")
        db_session.add_all([socio, other])
        db_session.commit()

        monkeypatch.setattr(config_mod.COMPANY_DATA, "cuit", "30999888776")
        res = update_company_info(
            CompanyUpdateSchema(razon_social="Actualizada SA", cuit="30-71234567-8"),
            db=db_session,
        )
        assert res["status"] == "success"
        db_session.refresh(socio)
        assert socio.cuit == "30712345678"

        # Intentar cambiar al CUIT duplicado de `other` debe retornar HTTP 400 (no 500)
        with pytest.raises(HTTPException) as exc_dup:
            update_company_info(
                CompanyUpdateSchema(razon_social="Actualizada SA", cuit="30-11122233-4"),
                db=db_session,
            )
        assert exc_dup.value.status_code == 400
    finally:
        config_mod.COMPANY_DATA.cuit = orig_cuit
        config_mod.COMPANY_DATA.razon_social = orig_rs


