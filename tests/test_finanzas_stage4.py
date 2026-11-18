from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException

from src.database.models.finance.bancos import (
    Banco,
    Cuenta,
    Concepto,
    Clasificacion,
    Movimiento,
    CategoriaMovimiento,
    TipoMoneda,
)
from src.database.models.finance.comprobantes import (
    Proveedor,
    Comprobante,
    TipoDocumento,
    Personeria,
    CategoriaImpositiva,
    TipoComprobante,
    EstadoComprobante,
)
from src.database.models.finance.planes import Plan, SistemaMatematico, Denominador
from src.database.models.creditos.clientes import Provincia
from src.database.models.creditos.creditos import Credito, Cuota, TipoCredito, EstadoCuota
from src.database.models.creditos.carteras import Cartera, OperacionCartera, TipoOperacionCartera


class _NonClosingSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __getattr__(self, name):
        return getattr(self._session, name)


def _setup_banco_y_cuenta(db_session):
    banco = Banco(nombre_banco="Banco Test Stage4", parser_type="none")
    db_session.add(banco)
    db_session.flush()

    cuenta = Cuenta(
        nombre="Cuenta Test S4",
        banco_id=banco.id,
        nro="123456",
        cbu="0000000000000000000001",
        alias="cuenta.s4.test",
        tipo_cuenta="CC",
        moneda=TipoMoneda.PESOS,
    )
    db_session.add(cuenta)
    db_session.flush()
    return banco, cuenta


def _setup_proveedor(db_session):
    prov = Provincia(nombre="Buenos Aires Test")
    db_session.add(prov)
    db_session.flush()

    proveedor = Proveedor(
        razon_social="Proveedor Stage4 SA",
        tipo_documento=TipoDocumento.CUIT,
        nro_documento="30777777771",
        personeria=Personeria.JURIDICA,
        provincia_id=prov.id,
        categoria_impositiva=CategoriaImpositiva.RESPONSABLE_INSCRIPTO,
    )
    db_session.add(proveedor)
    db_session.flush()
    return proveedor


def test_kpis_y_movimientos_decimal_sin_typeerror(db_session):
    from src.api.routes.finanzas import get_cuenta_kpis, get_kpis_globales, get_movimientos

    _, cuenta = _setup_banco_y_cuenta(db_session)
    clasif = Clasificacion(name="Operativo")
    db_session.add(clasif)
    db_session.flush()

    c_ing = Concepto(name="Cobro S4", tipo_movimiento=CategoriaMovimiento.INGRESO, clasificacion_id=clasif.id)
    c_egr = Concepto(name="Pago S4", tipo_movimiento=CategoriaMovimiento.EGRESO, clasificacion_id=clasif.id)
    c_fci = Concepto(name="Suscripcion FCI S4", tipo_movimiento=CategoriaMovimiento.SUSCRIPCION_FCI, clasificacion_id=clasif.id)
    db_session.add_all([c_ing, c_egr, c_fci])
    db_session.flush()

    db_session.add_all([
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 1), monto=Decimal("1000.50"), concepto_id=c_ing.id),
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 2), monto=Decimal("250.25"), concepto_id=c_egr.id),
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 3), monto=Decimal("300.00"), concepto_id=c_fci.id),
    ])
    db_session.commit()

    kpis_cta = get_cuenta_kpis(cuenta_id=cuenta.id, db=db_session)
    assert kpis_cta["saldo"] == 450.25
    assert kpis_cta["saldo_fci"] == 300.00

    kpis_glob = get_kpis_globales(db=db_session)
    assert kpis_glob["saldo"] == 450.25
    assert kpis_glob["ingresos_periodo"] == 1000.50
    assert kpis_glob["egresos_periodo"] == 550.25

    movs_res = get_movimientos(cuenta_id=cuenta.id, db=db_session)
    assert len(movs_res["items"]) == 3
    assert movs_res["items"][0].saldo_disponible in (1000.50, 250.25, 300.00)


def test_update_plan_vencimiento_primer_mes(db_session):
    from src.api.routes.planes import create_plan, update_plan
    from src.api.schemas.planes import PlanCreate

    proveedor = _setup_proveedor(db_session)
    db_session.commit()

    primer_vto = date(2026, 10, 15)
    plan_req = PlanCreate(
        id_origen="PLAN-S4-001",
        fecha=date(2026, 9, 15),
        proveedor_id=proveedor.id,
        capital=Decimal("12000.00"),
        anticipo=Decimal("0.00"),
        plazo=3,
        valor_cuota=Decimal("4200.00"),
        primer_vencimiento=primer_vto,
        sistema=SistemaMatematico.DIRECTO,
        denominador=Denominador.MENSUAL,
        tna=Decimal("0.0"),
    )
    created = create_plan(plan_req, db=db_session)
    cuotas_ini = sorted(created.cuotas, key=lambda c: c.numero_comprobante)
    assert cuotas_ini[0].fecha_vencimiento == primer_vto

    plan_upd = PlanCreate(
        id_origen="PLAN-S4-001",
        fecha=date(2026, 9, 15),
        proveedor_id=proveedor.id,
        capital=Decimal("12000.00"),
        anticipo=Decimal("0.00"),
        plazo=3,
        valor_cuota=Decimal("4300.00"),
        primer_vencimiento=primer_vto,
        sistema=SistemaMatematico.DIRECTO,
        denominador=Denominador.MENSUAL,
        tna=Decimal("0.0"),
    )
    updated = update_plan(created.id, plan_upd, db=db_session)
    cuotas_upd = sorted(updated.cuotas, key=lambda c: c.numero_comprobante)
    assert cuotas_upd[0].fecha_vencimiento == primer_vto
    assert cuotas_upd[1].fecha_vencimiento == date(2026, 11, 15)
    assert cuotas_upd[2].fecha_vencimiento == date(2026, 12, 15)


def test_comprobante_autocalculo_iva_y_topes_cancelacion(db_session):
    from src.api.routes.comprobantes import create_comprobante, create_cancelacion
    from src.api.schemas.comprobantes import ComprobanteCreate, CancelacionCreate

    _, cuenta = _setup_banco_y_cuenta(db_session)
    proveedor = _setup_proveedor(db_session)
    c_egr = Concepto(name="Pago Proveedor S4", tipo_movimiento=CategoriaMovimiento.EGRESO)
    db_session.add(c_egr)
    db_session.flush()

    mov = Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 5), monto=Decimal("500.00"), concepto_id=c_egr.id)
    db_session.add(mov)
    db_session.commit()

    comp = create_comprobante(
        ComprobanteCreate(
            proveedor_id=proveedor.id,
            tipo_comprobante=TipoComprobante.A,
            punto_venta=1,
            numero_comprobante=101,
            fecha_contable=date(2026, 8, 5),
            fecha_emision=date(2026, 8, 5),
            neto_gravado_21=Decimal("1000.00"),
        ),
        db=db_session,
    )
    assert comp.iva_21 == Decimal("210.00")
    assert comp.importe_total == Decimal("1210.00")

    with pytest.raises(HTTPException) as exc_neg:
        create_cancelacion(
            comp.id,
            CancelacionCreate(importe=Decimal("0.00"), fecha_cancelacion=date(2026, 8, 6)),
            db=db_session,
        )
    assert exc_neg.value.status_code == 400

    with pytest.raises(HTTPException) as exc_mov_over:
        create_cancelacion(
            comp.id,
            CancelacionCreate(importe=Decimal("600.00"), fecha_cancelacion=date(2026, 8, 6), movimiento_id=mov.id),
            db=db_session,
        )
    assert exc_mov_over.value.status_code == 400

    create_cancelacion(
        comp.id,
        CancelacionCreate(importe=Decimal("500.00"), fecha_cancelacion=date(2026, 8, 6), movimiento_id=mov.id),
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_comp_over:
        create_cancelacion(
            comp.id,
            CancelacionCreate(importe=Decimal("800.00"), fecha_cancelacion=date(2026, 8, 7)),
            db=db_session,
        )
    assert exc_comp_over.value.status_code == 400

    create_cancelacion(
        comp.id,
        CancelacionCreate(importe=Decimal("710.00"), fecha_cancelacion=date(2026, 8, 7)),
        db=db_session,
    )
    db_session.refresh(comp)
    assert comp.estado == EstadoComprobante.PAGADO


def test_posicion_iva_e_iibb_notas_credito_vep_y_retenciones(db_session):
    from src.api.routes.posicion_iva import calcular_posicion as calc_iva
    from src.api.routes.posicion_iibb import calcular_posicion as calc_iibb

    _, cuenta = _setup_banco_y_cuenta(db_session)
    proveedor = _setup_proveedor(db_session)

    c_ret_iva = Concepto(name="ARCA - Retención IVA", tipo_movimiento=CategoriaMovimiento.EGRESO)
    c_vep_iva = Concepto(name="Pago VEP IVA", tipo_movimiento=CategoriaMovimiento.EGRESO)
    c_sircreb = Concepto(name="SIRCREB Bancario", tipo_movimiento=CategoriaMovimiento.EGRESO)
    db_session.add_all([c_ret_iva, c_vep_iva, c_sircreb])
    db_session.flush()

    # Factura A: IVA=210, Percepcion IIBB=30
    fac_a = Comprobante(
        proveedor_id=proveedor.id,
        tipo_comprobante=TipoComprobante.A,
        punto_venta=1,
        numero_comprobante=201,
        fecha_contable=date(2026, 8, 10),
        fecha_emision=date(2026, 8, 10),
        neto_gravado_21=Decimal("1000.00"),
        iva_21=Decimal("210.00"),
        percepcion_iibb=Decimal("30.00"),
        importe_total=Decimal("1240.00"),
    )
    # Nota de Crédito A: IVA=105, Percepcion IIBB=10 (debe restar)
    nc_a = Comprobante(
        proveedor_id=proveedor.id,
        tipo_comprobante=TipoComprobante.NOTA_CREDITO_A,
        punto_venta=1,
        numero_comprobante=202,
        fecha_contable=date(2026, 8, 11),
        fecha_emision=date(2026, 8, 11),
        neto_gravado_21=Decimal("500.00"),
        iva_21=Decimal("105.00"),
        percepcion_iibb=Decimal("10.00"),
        importe_total=Decimal("615.00"),
    )
    # Comprobante VEP IVA: debe restar en saldo_a_pagar
    vep_iva = Comprobante(
        proveedor_id=proveedor.id,
        tipo_comprobante=TipoComprobante.VEP,
        punto_venta=1,
        numero_comprobante=203,
        concepto_id=c_vep_iva.id,
        fecha_contable=date(2026, 8, 12),
        fecha_emision=date(2026, 8, 12),
        importe_total=Decimal("50.00"),
    )
    db_session.add_all([fac_a, nc_a, vep_iva])

    # Movimientos bancarios: la retención IVA suma 20, el pago VEP IVA (50) NO debe duplicarse como retención
    db_session.add_all([
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 10), monto=Decimal("20.00"), concepto_id=c_ret_iva.id),
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 12), monto=Decimal("50.00"), concepto_id=c_vep_iva.id),
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 12), monto=Decimal("15.00"), concepto_id=c_sircreb.id),
    ])
    db_session.commit()

    res_iva = calc_iva(anio=2026, mes=8, db=db_session)
    assert res_iva["iva_compras"] == 105.00  # 210 - 105
    assert res_iva["retenciones_bancarias"] == 20.00  # Excluye "Pago VEP IVA"
    assert res_iva["pagos_vep"] == 50.00
    assert res_iva["saldo_a_pagar"] == round(0.0 - 105.00 - 20.00 - 0.0 + 0.0 - 50.00, 2)

    res_iibb = calc_iibb(anio=2026, mes=8, db=db_session)
    assert res_iibb["percepciones_compras"] == 20.00  # 30 - 10
    assert res_iibb["retenciones_bancarias"] == 15.00


def test_reportes_finance_comprobantes_cartera_y_esp(db_session, dummy_cliente, dummy_socio, monkeypatch):
    from src.reports.finance import comprobantes as rep_comp, cartera as rep_cart, esp as rep_esp

    factory = lambda: _NonClosingSessionProxy(db_session)
    monkeypatch.setattr("src.reports.finance.comprobantes.SessionLocal", factory)
    monkeypatch.setattr("src.reports.finance.cartera.SessionLocal", factory)
    monkeypatch.setattr("src.reports.finance.bancos.SessionLocal", factory)
    monkeypatch.setattr("src.reports.finance.esp.SessionLocal", factory)
    monkeypatch.setattr("src.logic.deuda.reportes.SessionLocal", factory)
    monkeypatch.setattr("src.logic.deuda.series.SessionLocal", factory)
    monkeypatch.setattr("src.logic.deuda.ctas_ctes.SessionLocal", factory)
    monkeypatch.setattr("src.reports.balances.engine", db_session.get_bind())

    # 1. Cartera vacía no debe fallar
    df_cart_empty = rep_cart.get_df()
    assert df_cart_empty.empty

    # 2. Cartera VENTA con una cuota comercializada y otra no comercializada
    cartera_v = Cartera(
        nombre="Cartera Venta S4",
        fecha_compra=date(2026, 8, 1),
        socio_id=dummy_socio.id,
        iva=False,
        recurso=False,
        tna_descuento=0.365,
        tipo_operacion=TipoOperacionCartera.VENTA,
    )
    cred = Credito(
        cliente_cuil=dummy_cliente.cuil,
        socio_originador_id=dummy_socio.id,
        capital=200.00,
        tna_c_iva=0.50,
        plazo=2,
        fecha_emision=date(2026, 7, 1),
        tipo_credito=TipoCredito.FRANCES,
    )
    db_session.add_all([cartera_v, cred])
    db_session.flush()

    q1 = Cuota(credito_id=cred.id, nro_cuota=1, fecha_vencimiento=date(2026, 9, 1), capital=100.0, interes=10.0, iva=2.1, estado=EstadoCuota.PENDIENTE)
    q2 = Cuota(credito_id=cred.id, nro_cuota=2, fecha_vencimiento=date(2026, 10, 1), capital=100.0, interes=10.0, iva=2.1, estado=EstadoCuota.PENDIENTE)
    db_session.add_all([q1, q2])
    db_session.flush()

    db_session.add_all([
        OperacionCartera(cuota_id=q1.id, cartera_id=cartera_v.id, cuota_comercializada=True, fecha_registro=date(2026, 8, 1)),
        OperacionCartera(cuota_id=q2.id, cartera_id=cartera_v.id, cuota_comercializada=False, fecha_registro=date(2026, 8, 1)),
    ])

    proveedor = _setup_proveedor(db_session)
    clasif_gastos = Clasificacion(name="Gastos Generales")
    db_session.add(clasif_gastos)
    db_session.flush()
    conc_gastos = Concepto(name="Factura Proveedor", tipo_movimiento=CategoriaMovimiento.EGRESO, clasificacion_id=clasif_gastos.id)
    db_session.add(conc_gastos)
    db_session.flush()

    db_session.add(
        Comprobante(
            proveedor_id=proveedor.id,
            concepto_id=conc_gastos.id,
            tipo_comprobante=TipoComprobante.A,
            punto_venta=1,
            numero_comprobante=301,
            fecha_contable=date(2026, 8, 1),
            fecha_emision=date(2026, 8, 1),
            neto_gravado_21=Decimal("1000.00"),
            iva_21=Decimal("210.00"),
            importe_total=Decimal("1210.00"),
        )
    )
    db_session.commit()

    df_cart = rep_cart.get_df()
    assert len(df_cart) == 1
    assert float(df_cart.iloc[0]["importe_nominal"]) == 110.0

    df_pend = rep_comp.pendientes(date(2026, 8, 31))
    assert len(df_pend) == 1
    assert float(df_pend.iloc[0]["saldo"]) == 1210.0

    df_esp = rep_esp.reporte(date(2026, 8, 31), n_periodos=1)
    assert not df_esp.empty
    assert ("Pasivos", "Facturas adeudadas") in df_esp.index
