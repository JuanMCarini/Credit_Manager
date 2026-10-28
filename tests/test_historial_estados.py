import pytest
from datetime import date
from src.database import get_db
from src.database.models import (
    Cliente,
    Credito,
    Cuota,
    EstadoCredito,
    EstadoClienteEnum,
    EstadoCuota,
    HistorialEstadoCredito,
    HistorialEstadoCliente,
    Usuario,
    Rol,
    TipoRolEnum,
)
from src.services.estado_audit import (
    registrar_cambio_estado_credito,
    registrar_cambio_estado_cliente,
)
from src.api.dependencies.auth import create_access_token


@pytest.fixture
def test_user(db_session):
    rol = db_session.query(Rol).filter(Rol.nombre == TipoRolEnum.ADMINISTRADOR).first()
    if not rol:
        rol = Rol(nombre=TipoRolEnum.ADMINISTRADOR)
        db_session.add(rol)
        db_session.flush()

    user = db_session.query(Usuario).filter(Usuario.email == "test_audit@test.com").first()
    if not user:
        user = Usuario(
            email="test_audit@test.com",
            hashed_password="fakehash",
            nombre_completo="Juan Auditor",
            rol_id=rol.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    return user


def test_historial_credito_transiciones(db_session, test_user):
    # Crear cliente dummy si no existe
    cli = db_session.query(Cliente).filter(Cliente.cuil == "20999999994").first()
    if not cli:
        cli = Cliente(
            cuil="20999999994",
            documento="99999994",
            apellido="TestAudit",
            nombre="Cliente",
            estado=EstadoClienteEnum.ACTIVO,
        )
        db_session.add(cli)
        db_session.commit()

    # 1. Crear crédito
    credito = Credito(
        cliente_cuil=cli.cuil,
        capital=50000.0,
        tna_c_iva=0.60,
        plazo=6,
        fecha_emision=date.today(),
        estado=EstadoCredito.APROBADO,
        dia_vencimiento=28,
    )
    db_session.add(credito)
    db_session.commit()

    # 2. Registrar alta inicial
    reg1 = registrar_cambio_estado_credito(
        db=db_session,
        credito=credito,
        nuevo_estado=EstadoCredito.APROBADO,
        usuario_id=test_user.id,
        origen="ORIGINACION",
        motivo="Crédito originado y aprobado",
        forzar_registro=True,
    )
    db_session.commit()
    assert reg1 is not None
    assert reg1.estado_nuevo == "APROBADO"
    assert reg1.origen == "ORIGINACION"
    assert reg1.usuario_id == test_user.id

    # 3. Transición a FIRMADO
    reg2 = registrar_cambio_estado_credito(
        db=db_session,
        credito=credito,
        nuevo_estado=EstadoCredito.FIRMADO,
        usuario_id=test_user.id,
        origen="LEGAJO_FIRMA",
        motivo="Legajo firmado y cargado",
    )
    db_session.commit()
    assert reg2 is not None
    assert reg2.estado_anterior == "APROBADO"
    assert reg2.estado_nuevo == "FIRMADO"
    assert credito.estado == EstadoCredito.FIRMADO

    # 4. Transición a JUDICIAL con motivo
    reg3 = registrar_cambio_estado_credito(
        db=db_session,
        credito=credito,
        nuevo_estado=EstadoCredito.JUDICIAL,
        usuario_id=test_user.id,
        origen="MANUAL",
        motivo="Derivado a estudio jurídico por mora superior a 90 días",
    )
    db_session.commit()
    assert reg3 is not None
    assert reg3.estado_anterior == "FIRMADO"
    assert reg3.estado_nuevo == "JUDICIAL"
    assert reg3.motivo == "Derivado a estudio jurídico por mora superior a 90 días"

    # 5. Verificar relación y orden
    db_session.refresh(credito)
    historial = credito.historial_estados
    assert len(historial) >= 3
    assert historial[0].estado_nuevo == "JUDICIAL"


def test_historial_cliente_transiciones(db_session, test_user):
    cli = db_session.query(Cliente).filter(Cliente.cuil == "27999999981").first()
    if not cli:
        cli = Cliente(
            cuil="27999999981",
            documento="99999981",
            apellido="AuditClient",
            nombre="Prueba",
            estado=EstadoClienteEnum.ACTIVO,
        )
        db_session.add(cli)
        db_session.commit()

    # 1. Registrar estado inicial
    reg1 = registrar_cambio_estado_cliente(
        db=db_session,
        cliente=cli,
        nuevo_estado=EstadoClienteEnum.ACTIVO,
        usuario_id=test_user.id,
        origen="ALTA_CLIENTE",
        motivo="Alta cliente",
        forzar_registro=True,
    )
    db_session.commit()
    assert reg1 is not None
    assert reg1.estado_nuevo == "ACTIVO"

    # 2. Pasar a INCOBRABLE
    reg2 = registrar_cambio_estado_cliente(
        db=db_session,
        cliente=cli,
        nuevo_estado=EstadoClienteEnum.INCOBRABLE,
        usuario_id=test_user.id,
        origen="MANUAL",
        motivo="Sin bienes embargables tras proceso judicial",
    )
    db_session.commit()
    assert reg2 is not None
    assert reg2.estado_anterior == "ACTIVO"
    assert reg2.estado_nuevo == "INCOBRABLE"
    assert cli.estado == EstadoClienteEnum.INCOBRABLE

    # 3. Verificar relación en el modelo
    db_session.refresh(cli)
    assert len(cli.historial_estados) >= 2
    assert cli.historial_estados[0].estado_nuevo == "INCOBRABLE"


def test_api_endpoints_historial(db_session, test_user):
    from fastapi.testclient import TestClient
    from src.api.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    token = create_access_token({"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        client = TestClient(app)

        # Crear clientes requeridos en la sesión limpia
        cli1 = Cliente(
            cuil="20999999994",
            documento="99999994",
            apellido="TestAudit",
            nombre="Cliente",
            estado=EstadoClienteEnum.ACTIVO,
        )
        cli2 = Cliente(
            cuil="27999999981",
            documento="99999981",
            apellido="AuditClient",
            nombre="Prueba",
            estado=EstadoClienteEnum.ACTIVO,
        )
        db_session.add_all([cli1, cli2])
        db_session.commit()

        registrar_cambio_estado_cliente(
            db=db_session,
            cliente=cli2,
            nuevo_estado=EstadoClienteEnum.ACTIVO,
            usuario_id=test_user.id,
            origen="ALTA_CLIENTE",
            motivo="Alta cliente",
            forzar_registro=True,
        )

        # 1. Crear un crédito para probar el endpoint
        credito = Credito(
            cliente_cuil="20999999994",
            capital=25000.0,
            tna_c_iva=0.55,
            plazo=3,
            fecha_emision=date.today(),
            estado=EstadoCredito.APROBADO,
            dia_vencimiento=28,
        )
        db_session.add(credito)
        db_session.commit()

        registrar_cambio_estado_credito(
            db=db_session,
            credito=credito,
            nuevo_estado=EstadoCredito.APROBADO,
            usuario_id=test_user.id,
            origen="ORIGINACION",
            motivo="Aprobado en originación",
            forzar_registro=True,
        )
        registrar_cambio_estado_credito(
            db=db_session,
            credito=credito,
            nuevo_estado=EstadoCredito.FIRMADO,
            usuario_id=test_user.id,
            origen="LEGAJO_FIRMA",
            motivo="Firma digital verificada",
        )
        db_session.commit()

        # GET historial credito
        res_cred = client.get(f"/api/v1/creditos/{credito.id}/historial-estados", headers=headers)
        assert res_cred.status_code == 200
        data_cred = res_cred.json()
        assert len(data_cred) >= 2
        assert data_cred[0]["estado_nuevo"] == "FIRMADO"
        assert data_cred[0]["motivo"] == "Firma digital verificada"
        assert data_cred[0]["usuario_nombre"] == "Juan Auditor"

        # GET historial cliente
        res_cli = client.get("/api/v1/clientes/27999999981/historial-estados", headers=headers)
        assert res_cli.status_code == 200
        data_cli = res_cli.json()
        assert len(data_cli) >= 1
        assert data_cli[0]["cliente_cuil"] == "27999999981"
    finally:
        app.dependency_overrides.clear()
