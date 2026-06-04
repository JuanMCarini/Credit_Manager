# pyrefly: ignore [missing-import]
import pytest
from datetime import date
from src.api.main import get_cliente_cuenta_corriente
from src.database import Cliente, Credito, Cuota, Cobranza, TipoCobranzaEnum
from src.database.models import EstadoCredito, EstadoCuota

def test_api_cuenta_corriente(db_session, dummy_cliente):
    # Create a Credito for the dummy client
    credito = Credito(
        cliente_cuil=dummy_cliente.cuil,
        capital=10000.0,
        tna_c_iva=0.45,
        plazo=2,
        fecha_emision=date(2026, 6, 1),
        estado=EstadoCredito.ACTIVO,
        dia_vencimiento=28
    )
    db_session.add(credito)
    db_session.commit()
    
    # Create two Cuotas
    cuota1 = Cuota(
        credito_id=credito.id,
        nro_cuota=1,
        fecha_vencimiento=date(2026, 7, 28),
        capital=5000.0,
        interes=200.0,
        iva=42.0,
        estado=EstadoCuota.PENDIENTE
    )
    cuota2 = Cuota(
        credito_id=credito.id,
        nro_cuota=2,
        fecha_vencimiento=date(2026, 8, 28),
        capital=5000.0,
        interes=100.0,
        iva=21.0,
        estado=EstadoCuota.PENDIENTE
    )
    db_session.add_all([cuota1, cuota2])
    db_session.commit()
    
    # Add a Cobranza to cuota1
    cobranza = Cobranza(
        cuota_id=cuota1.id,
        tipo_cobranza=TipoCobranzaEnum.COMUN.value,
        capital=5000.0,
        interes=200.0,
        iva=42.0,
        fecha=date(2026, 7, 25)
    )
    db_session.add(cobranza)
    db_session.commit()
    
    # Call the controller directly
    data = get_cliente_cuenta_corriente(dummy_cliente.cuil, db_session)
    assert len(data) == 2
    
    # Verify cuota1
    assert data[0]["credito_id"] == credito.id
    assert data[0]["nro_cuota"] == 1
    assert data[0]["total_esperado"] == 5242.0
    assert data[0]["total_cobrado"] == 5242.0
    assert data[0]["saldo_pendiente"] == 0.0
    assert len(data[0]["detalle_cobranzas"]) == 1
    assert data[0]["detalle_cobranzas"][0]["total"] == 5242.0
    
    # Verify cuota2
    assert data[1]["nro_cuota"] == 2
    assert data[1]["total_esperado"] == 5121.0
    assert data[1]["total_cobrado"] == 0.0
    assert data[1]["saldo_pendiente"] == 5121.0
    assert len(data[1]["detalle_cobranzas"]) == 0
