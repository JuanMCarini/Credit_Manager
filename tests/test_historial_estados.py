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


def _can_create_loopback_socketpair() -> bool:
    import socket
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lsock.bind(("127.0.0.1", 0))
        lsock.listen(1)
        lsock.settimeout(0.05)
        addr, port = lsock.getsockname()[:2]
        csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            csock.settimeout(0.05)
            csock.connect((addr, port))
            ssock, _ = lsock.accept()
            ssock.close()
            return True
        except OSError:
            return False
        finally:
            csock.close()
    except OSError:
        return False
    finally:
        lsock.close()


def test_api_endpoints_historial(db_session, test_user):
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

    if _can_create_loopback_socketpair():
        from fastapi.testclient import TestClient
        from src.api.main import app

        app.dependency_overrides[get_db] = lambda: db_session
        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        try:
            client = TestClient(app)

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
    else:
        from src.api.routes.creditos import get_historial_credito_estados
        from src.api.routes.clientes import get_historial_cliente_estados

        data_cred = [
            item.model_dump()
            for item in get_historial_credito_estados(credito_id=credito.id, db=db_session)
        ]
        assert len(data_cred) >= 2
        assert data_cred[0]["estado_nuevo"] == "FIRMADO"
        assert data_cred[0]["motivo"] == "Firma digital verificada"
        assert data_cred[0]["usuario_nombre"] == "Juan Auditor"

        data_cli = [
            item.model_dump()
            for item in get_historial_cliente_estados(cuil="27999999981", db=db_session)
        ]
        assert len(data_cli) >= 1
        assert data_cli[0]["cliente_cuil"] == "27999999981"


def test_update_cliente_registra_historial_y_reactiva_incobrable(db_session, test_user):
    from datetime import timedelta
    from src.api.routes.clientes import update_cliente
    from src.api.routes.creditos import update_credito_estado
    from src.api.schemas.clientes import ClienteCreate
    from src.api.schemas.creditos import CreditoEstadoUpdate

    cli = Cliente(
        cuil="20888888887",
        documento="88888887",
        apellido="Cascada",
        nombre="Tester",
        estado=EstadoClienteEnum.ACTIVO,
    )
    db_session.add(cli)
    db_session.flush()

    cred = Credito(
        cliente_cuil=cli.cuil,
        capital=10000.0,
        tna_c_iva=0.50,
        plazo=1,
        fecha_emision=date.today(),
        estado=EstadoCredito.ACTIVO,
        dia_vencimiento=28,
    )
    db_session.add(cred)
    db_session.flush()

    cuota_futura = Cuota(
        credito_id=cred.id,
        nro_cuota=1,
        fecha_vencimiento=date.today() + timedelta(days=30),
        capital=10000.0,
        interes=500.0,
        iva=105.0,
        estado=EstadoCuota.PENDIENTE,
    )
    db_session.add(cuota_futura)
    db_session.commit()

    # 1. Pasar cliente a INCOBRABLE via update_cliente
    update_cliente(
        cuil=cli.cuil,
        cliente_data=ClienteCreate(
            cuil=cli.cuil,
            documento=cli.documento,
            apellido=cli.apellido,
            nombre=cli.nombre,
            estado=EstadoClienteEnum.INCOBRABLE,
            motivo_estado="Declarado incobrable",
        ),
        db=db_session,
        current_user=test_user,
    )

    db_session.refresh(cli)
    db_session.refresh(cred)
    db_session.refresh(cuota_futura)
    assert cli.estado == EstadoClienteEnum.INCOBRABLE
    assert cred.estado == EstadoCredito.INCOBRABLE
    assert cuota_futura.estado == EstadoCuota.INCOBRABLE

    hist_cli = db_session.query(HistorialEstadoCliente).filter_by(cliente_cuil=cli.cuil).all()
    assert any(h.estado_anterior == "ACTIVO" and h.estado_nuevo == "INCOBRABLE" for h in hist_cli)

    # 2. Reactivar cliente a ACTIVO via update_cliente
    update_cliente(
        cuil=cli.cuil,
        cliente_data=ClienteCreate(
            cuil=cli.cuil,
            documento=cli.documento,
            apellido=cli.apellido,
            nombre=cli.nombre,
            estado=EstadoClienteEnum.ACTIVO,
            motivo_estado="Rehabilitación de cuenta",
        ),
        db=db_session,
        current_user=test_user,
    )

    db_session.refresh(cli)
    db_session.refresh(cred)
    db_session.refresh(cuota_futura)
    assert cli.estado == EstadoClienteEnum.ACTIVO
    assert cred.estado == EstadoCredito.ACTIVO
    assert cuota_futura.estado == EstadoCuota.PENDIENTE

    hist_cred = db_session.query(HistorialEstadoCredito).filter_by(credito_id=cred.id).all()
    assert any(h.estado_anterior == "INCOBRABLE" and h.estado_nuevo == "ACTIVO" for h in hist_cred)

    # 3. Verificar reactivación directa vía update_credito_estado
    update_credito_estado(
        credito_id=cred.id,
        data=CreditoEstadoUpdate(estado="INCOBRABLE", motivo="Prueba directa"),
        db=db_session,
        current_user=test_user,
    )
    db_session.refresh(cuota_futura)
    assert cuota_futura.estado == EstadoCuota.INCOBRABLE

    update_credito_estado(
        credito_id=cred.id,
        data=CreditoEstadoUpdate(estado="ACTIVO", motivo="Reactivación directa"),
        db=db_session,
        current_user=test_user,
    )
    db_session.refresh(cred)
    db_session.refresh(cuota_futura)
    assert cred.estado == EstadoCredito.ACTIVO
    assert cuota_futura.estado == EstadoCuota.PENDIENTE


def test_delete_credito_aprobado_y_firmado_con_historial(db_session, test_user, tmp_path, monkeypatch):
    from datetime import timedelta
    from fastapi import HTTPException
    from src.api.routes.creditos import delete_credito
    from src.database.models import DocumentoLegajo, Transferencia

    monkeypatch.setattr("src.api.routes.creditos.UPLOAD_DIR", str(tmp_path))

    cli = Cliente(
        cuil="20777777771",
        documento="77777771",
        apellido="Delete",
        nombre="Tester",
        estado=EstadoClienteEnum.ACTIVO,
    )
    db_session.add(cli)
    db_session.commit()

    def _crear_credito_con_dependencias(estado_inicial: EstadoCredito, suffix: str) -> tuple[Credito, str]:
        cred = Credito(
            cliente_cuil=cli.cuil,
            capital=15000.0,
            tna_c_iva=0.50,
            plazo=1,
            fecha_emision=date.today(),
            estado=EstadoCredito.APROBADO,
            dia_vencimiento=28,
        )
        db_session.add(cred)
        db_session.flush()

        cuota = Cuota(
            credito_id=cred.id,
            nro_cuota=1,
            fecha_vencimiento=date.today() + timedelta(days=30),
            capital=15000.0,
            interes=750.0,
            iva=157.5,
            estado=EstadoCuota.PENDIENTE,
        )
        transf = Transferencia(
            cbu="0110285930028521696929",
            monto=15000.0,
            cuit=cli.cuil,
            credito_id=cred.id,
            razon_social="Delete Tester",
        )
        db_session.add_all([cuota, transf])
        db_session.flush()

        filename = f"legajo_{suffix}.pdf"
        stored_name = f"{cred.id}_{filename}"
        file_path = tmp_path / stored_name
        file_path.write_bytes(b"%PDF-1.4 test")

        doc = DocumentoLegajo(
            credito_id=cred.id,
            nombre_archivo=filename,
            ruta_archivo=str(file_path),
            tipo_archivo="application/pdf",
            transferencia_id=transf.id,
        )
        db_session.add(doc)

        registrar_cambio_estado_credito(
            db=db_session,
            credito=cred,
            nuevo_estado=EstadoCredito.APROBADO,
            usuario_id=test_user.id,
            origen="ORIGINACION",
            motivo="Alta inicial",
            forzar_registro=True,
        )
        if estado_inicial != EstadoCredito.APROBADO:
            registrar_cambio_estado_credito(
                db=db_session,
                credito=cred,
                nuevo_estado=estado_inicial,
                usuario_id=test_user.id,
                origen="MANUAL",
                motivo=f"Paso a {estado_inicial.value}",
            )
        db_session.commit()
        return cred, str(file_path)

    # 1. Eliminar crédito en estado APROBADO con historial, cuota, transferencia y documento
    cred_aprobado, path_aprobado = _crear_credito_con_dependencias(EstadoCredito.APROBADO, "aprobado")
    cred_aprobado_id = cred_aprobado.id
    res_aprobado = delete_credito(credito_id=cred_aprobado_id, db=db_session)
    assert res_aprobado["status"] == "success"
    assert db_session.query(Credito).filter_by(id=cred_aprobado_id).first() is None
    assert db_session.query(Cuota).filter_by(credito_id=cred_aprobado_id).count() == 0
    assert db_session.query(Transferencia).filter_by(credito_id=cred_aprobado_id).count() == 0
    assert db_session.query(DocumentoLegajo).filter_by(credito_id=cred_aprobado_id).count() == 0
    assert db_session.query(HistorialEstadoCredito).filter_by(credito_id=cred_aprobado_id).count() == 0
    assert not (tmp_path / f"{cred_aprobado_id}_legajo_aprobado.pdf").exists()

    # 2. Eliminar crédito en estado FIRMADO con historial, cuota, transferencia y documento
    cred_firmado, path_firmado = _crear_credito_con_dependencias(EstadoCredito.FIRMADO, "firmado")
    cred_firmado_id = cred_firmado.id
    res_firmado = delete_credito(credito_id=cred_firmado_id, db=db_session)
    assert res_firmado["status"] == "success"
    assert db_session.query(Credito).filter_by(id=cred_firmado_id).first() is None
    assert db_session.query(Cuota).filter_by(credito_id=cred_firmado_id).count() == 0
    assert db_session.query(Transferencia).filter_by(credito_id=cred_firmado_id).count() == 0
    assert db_session.query(DocumentoLegajo).filter_by(credito_id=cred_firmado_id).count() == 0
    assert db_session.query(HistorialEstadoCredito).filter_by(credito_id=cred_firmado_id).count() == 0
    assert not (tmp_path / f"{cred_firmado_id}_legajo_firmado.pdf").exists()

    db_session.refresh(cli)
    assert cli.estado == EstadoClienteEnum.INACTIVO

    # 3. Rechazar eliminación de crédito en estado ACTIVO
    cred_activo, _ = _crear_credito_con_dependencias(EstadoCredito.ACTIVO, "activo")
    with pytest.raises(HTTPException) as exc_info:
        delete_credito(credito_id=cred_activo.id, db=db_session)
    assert exc_info.value.status_code == 400
    assert "APROBADO o FIRMADO" in exc_info.value.detail
    assert db_session.query(Credito).filter_by(id=cred_activo.id).first() is not None
