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
    RolSistemaConcepto,
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

    c_ret_iva = Concepto(
        name="ARCA - Retención IVA",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        rol_sistema=RolSistemaConcepto.RETENCION_IVA.value,
    )
    c_iva_gasto = Concepto(
        name="IVA Resp. Inscripto",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        rol_sistema=None,
    )
    c_vep_iva = Concepto(
        name="Pago VEP IVA",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        rol_sistema=RolSistemaConcepto.VEP_IVA.value,
    )
    c_sircreb = Concepto(
        name="Débito Bancario Jurisdiccional",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        rol_sistema=RolSistemaConcepto.RETENCION_IIBB.value,
    )
    db_session.add_all([c_ret_iva, c_iva_gasto, c_vep_iva, c_sircreb])
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

    # Movimientos bancarios: la retención IVA suma 20; ni VEP IVA (50) ni "IVA Resp. Inscripto" (100 sin rol) deben contarse como retención
    db_session.add_all([
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 10), monto=Decimal("20.00"), concepto_id=c_ret_iva.id),
        Movimiento(cuenta_id=cuenta.id, fecha=date(2026, 8, 11), monto=Decimal("100.00"), concepto_id=c_iva_gasto.id),
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

    _, cuenta = _setup_banco_y_cuenta(db_session)
    proveedor = _setup_proveedor(db_session)
    clasif_gastos = Clasificacion(name="Gastos Generales")
    db_session.add(clasif_gastos)
    db_session.flush()
    conc_gastos = Concepto(name="Factura Proveedor", tipo_movimiento=CategoriaMovimiento.EGRESO, clasificacion_id=clasif_gastos.id)
    conc_plan_gan = Concepto(
        name="Plan Mis Facilidades Ganancias",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        rol_sistema=RolSistemaConcepto.PLAN_PAGO_GANANCIAS.value,
    )
    conc_venta = Concepto(
        name="Cobro Cesión de Cartera",
        tipo_movimiento=CategoriaMovimiento.INGRESO,
        rol_sistema=RolSistemaConcepto.VENTA_CARTERA.value,
    )
    conc_pf_in = Concepto(
        name="Constitución Plazo Fijo Test",
        tipo_movimiento=CategoriaMovimiento.PLAZO_FIJO_INGRESOS,
    )
    db_session.add_all([conc_gastos, conc_plan_gan, conc_venta, conc_pf_in])
    db_session.flush()

    db_session.add_all([
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
        ),
        Comprobante(
            proveedor_id=proveedor.id,
            concepto_id=conc_plan_gan.id,
            tipo_comprobante=TipoComprobante.CUOTA,
            punto_venta=1,
            numero_comprobante=302,
            fecha_contable=date(2026, 8, 5),
            fecha_emision=date(2026, 8, 5),
            importe_total=Decimal("400.00"),
        ),
        Movimiento(
            cuenta_id=cuenta.id,
            fecha=date(2026, 8, 10),
            monto=Decimal("500.00"),
            concepto_id=conc_pf_in.id,
        ),
        Movimiento(
            cuenta_id=cuenta.id,
            fecha=date(2026, 8, 12),
            monto=Decimal("50.00"),
            concepto_id=conc_venta.id,
        ),
    ])
    db_session.commit()

    df_cart = rep_cart.get_df()
    assert len(df_cart) == 1
    assert float(df_cart.iloc[0]["importe_nominal"]) == 110.0

    df_pend = rep_comp.pendientes(date(2026, 8, 31))
    assert len(df_pend) == 2

    df_esp = rep_esp.reporte(date(2026, 8, 31), n_periodos=1)
    assert not df_esp.empty
    col = df_esp.columns[0]
    assert ("Pasivos", "Facturas adeudadas") in df_esp.index
    assert float(df_esp.loc[("Pasivos", "Facturas adeudadas"), col]) == -1210.0
    assert ("Pasivos", "Planes de Pago Ganancias") in df_esp.index
    assert float(df_esp.loc[("Pasivos", "Planes de Pago Ganancias"), col]) == -400.0
    assert ("Activos", "Inversiones (Plazo Fijo)") in df_esp.index
    assert float(df_esp.loc[("Activos", "Inversiones (Plazo Fijo)"), col]) == 500.0


def test_import_extract_via_tabla_relaciones_y_clasificacion(db_session, monkeypatch):
    import io
    import pandas as pd
    from src.database.models.socios import Relacion, SocioComercial
    from src.database.seed_bancos import seed_bancos
    from src.database.seed_conceptos import seed_conceptos
    from src.logic.creditos.import_data.bancos.bica import import_extract as bica_import
    from src.logic.creditos.import_data.bancos.pampa import import_extract as pampa_import
    from src.logic.creditos.import_data.bancos.santander import import_extract as santander_import
    from src.api.routes.finanzas import update_movimiento, update_movimiento_bulk
    from src.api.routes.auxiliares import delete_aux_record
    from src.api.schemas.bancos import MovimientoUpdate, MovimientoBulkConceptoUpdate

    factory = lambda: _NonClosingSessionProxy(db_session)
    monkeypatch.setattr("src.logic.creditos.import_data.bancos.bica.SessionLocal", factory)
    monkeypatch.setattr("src.logic.creditos.import_data.bancos.pampa.SessionLocal", factory)
    monkeypatch.setattr("src.logic.creditos.import_data.bancos.santander.SessionLocal", factory)

    seed_conceptos(db_session)
    seed_bancos(db_session)

    # Verificar que seed_bancos no auto-crea socios comerciales duplicados
    assert db_session.query(SocioComercial).count() == 0

    socio_bica = SocioComercial(razon_social="BANCO BICA S.A.", cuit="30500057430")
    socio_santander = SocioComercial(razon_social="Banco Santander", cuit="30500008454")
    socio_pampa = SocioComercial(razon_social="Banco de La Pampa", cuit="30500010912")
    db_session.add_all([socio_bica, socio_santander, socio_pampa])
    db_session.commit()

    seed_bancos(db_session)
    assert db_session.query(SocioComercial).count() == 3

    conc_imp_debito = Concepto(
        name="Impuesto al Debito",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
        descripcion="Impuesto Ley 25.413",
    )
    conc_gastos_bco = Concepto(
        name="Gastos Bancarios",
        tipo_movimiento=CategoriaMovimiento.EGRESO,
    )
    db_session.add_all([conc_imp_debito, conc_gastos_bco])
    db_session.commit()

    banco_bica = db_session.query(Banco).filter_by(nombre_banco="Banco Bica").first()
    assert banco_bica is not None
    assert banco_bica.parser_type == "bica"
    assert banco_bica.socio_id == socio_bica.id

    cuenta_bica = Cuenta(
        nombre="Bica CC",
        banco_id=banco_bica.id,
        nro="1001",
        cbu="1111111111111111111111",
        alias="bica.test",
        tipo_cuenta="Cuenta Corriente",
        moneda=TipoMoneda.PESOS,
    )
    db_session.add(cuenta_bica)
    db_session.commit()

    # 1. Primera importación Bica sin relaciones cargadas -> todo debe ir directo a NO CLASIFICADO
    df_bica_1 = pd.DataFrame([
        {
            "Fec.Operación": "01/09/2026",
            "Fecha Real": "01/09/2026",
            "Transacción": "Impuesto al Débito Ley 25.413",
            "Info Adicional": None,
            "Comprobante": "101",
            "Importe": -1500.00,
        },
        {
            "Fec.Operación": "01/09/2026",
            "Fecha Real": "01/09/2026",
            "Transacción": "Comisión por Servicio de Cuenta",
            "Info Adicional": None,
            "Comprobante": "102",
            "Importe": -500.00,
        },
        {
            "Fec.Operación": "01/09/2026",
            "Fecha Real": "01/09/2026",
            "Transacción": "Acreditación Transferencia",
            "Info Adicional": "CUIT 30-12345678-9",
            "Comprobante": "103",
            "Importe": 25000.00,
        },
    ])
    excel_buf_1 = io.BytesIO()
    df_bica_1.to_excel(excel_buf_1, index=False)
    excel_buf_1.seek(0)
    bica_import(excel_buf_1, cuenta_bica.id)

    movs_1 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_bica.id).order_by(Movimiento.id).all()
    assert len(movs_1) == 3
    assert movs_1[0].concepto.name == "EGRESO NO CLASIFICADO"
    assert movs_1[1].concepto.name == "EGRESO NO CLASIFICADO"
    assert movs_1[2].concepto.name == "INGRESO NO CLASIFICADO"
    assert movs_1[2].descripcion == "Acreditación Transferencia"
    assert movs_1[2].info_adicional == "CUIT 30-12345678-9"

    # 2. Clasificación individual con guardar_relacion=True -> guarda relación en tabla relaciones
    update_movimiento(
        movs_1[0].id,
        MovimientoUpdate(concepto_id=conc_imp_debito.id, guardar_relacion=True),
        db=db_session,
    )
    rel_1 = (
        db_session.query(Relacion)
        .filter_by(
            socio_id=banco_bica.socio_id,
            tabla="conceptos",
            id_foraneo="Impuesto al Débito Ley 25.413",
        )
        .first()
    )
    assert rel_1 is not None
    assert rel_1.id_local == conc_imp_debito.id

    # También debe permitir mapear otro detalle distinto al mismo concepto (sin uq_socio_tabla_local)
    update_movimiento_bulk(
        MovimientoBulkConceptoUpdate(
            movimiento_ids=[movs_1[1].id],
            concepto_id=conc_imp_debito.id,
            guardar_relacion=True,
        ),
        db=db_session,
    )
    rel_2 = (
        db_session.query(Relacion)
        .filter_by(
            socio_id=banco_bica.socio_id,
            tabla="conceptos",
            id_foraneo="Comisión por Servicio de Cuenta",
        )
        .first()
    )
    assert rel_2 is not None
    assert rel_2.id_local == conc_imp_debito.id

    # 3. Segunda importación Bica -> existentes toman relación; los nuevos sin relación van a NO CLASIFICADO
    df_bica_2 = pd.DataFrame([
        {
            "Fec.Operación": "02/09/2026",
            "Fecha Real": "02/09/2026",
            "Transacción": "Impuesto al Débito Ley 25.413",
            "Info Adicional": None,
            "Comprobante": "201",
            "Importe": -2200.00,
        },
        {
            "Fec.Operación": "02/09/2026",
            "Fecha Real": "02/09/2026",
            "Transacción": "Comisión por Servicio de Cuenta",
            "Info Adicional": None,
            "Comprobante": "202",
            "Importe": -600.00,
        },
        {
            "Fec.Operación": "02/09/2026",
            "Fecha Real": "02/09/2026",
            "Transacción": "Débito Nuevo Desconocido",
            "Info Adicional": None,
            "Comprobante": "203",
            "Importe": -900.00,
        },
    ])
    excel_buf_2 = io.BytesIO()
    df_bica_2.to_excel(excel_buf_2, index=False)
    excel_buf_2.seek(0)
    bica_import(excel_buf_2, cuenta_bica.id)

    mov_201 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_bica.id, nro_comprobante="201").first()
    mov_202 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_bica.id, nro_comprobante="202").first()
    mov_203 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_bica.id, nro_comprobante="203").first()
    assert mov_201.concepto_id == conc_imp_debito.id
    assert mov_202.concepto_id == conc_imp_debito.id
    assert mov_203.concepto.name == "EGRESO NO CLASIFICADO"

    # 4. Verificar también Santander (limpieza de Ref) y Pampa usando tabla relaciones
    banco_santander = db_session.query(Banco).filter_by(nombre_banco="Banco Santander").first()
    cuenta_sant = Cuenta(
        nombre="Santander CC",
        banco_id=banco_santander.id,
        nro="2001",
        cbu="2222222222222222222222",
        alias="sant.test",
        tipo_cuenta="Cuenta Corriente",
        moneda=TipoMoneda.PESOS,
    )
    banco_pampa = db_session.query(Banco).filter_by(nombre_banco="Banco de La Pampa").first()
    cuenta_pampa = Cuenta(
        nombre="Pampa CC",
        banco_id=banco_pampa.id,
        nro="3001",
        cbu="3333333333333333333333",
        alias="pampa.test",
        tipo_cuenta="Cuenta Corriente",
        moneda=TipoMoneda.PESOS,
    )
    db_session.add_all([cuenta_sant, cuenta_pampa])
    db_session.commit()

    sant_csv_1 = (
        "Fecha;Concepto;Referencia;Cod. Operativo;Importe\n"
        "01/09/2026;Comision Mantenimiento;999;10;(1.000,00)\n"
    )
    santander_import(io.StringIO(sant_csv_1), cuenta_sant.id)
    mov_s1 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_sant.id).first()
    assert mov_s1.concepto.name == "EGRESO NO CLASIFICADO"
    assert mov_s1.descripcion == "Comision Mantenimiento"
    assert mov_s1.info_adicional == "Ref: 999"

    # Clasificamos el movimiento de Santander -> guarda relación limpia ("Comision Mantenimiento", sin "- Ref: 999")
    update_movimiento_bulk(
        MovimientoBulkConceptoUpdate(
            movimiento_ids=[mov_s1.id],
            concepto_id=conc_gastos_bco.id,
            guardar_relacion=True,
        ),
        db=db_session,
    )
    sant_csv_2 = (
        "Fecha;Concepto;Referencia;Cod. Operativo;Importe\n"
        "02/09/2026;Comision Mantenimiento;1000;11;(1.200,00)\n"
    )
    santander_import(io.StringIO(sant_csv_2), cuenta_sant.id)
    mov_s2 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_sant.id, nro_comprobante="1000").first()
    assert mov_s2.concepto_id == conc_gastos_bco.id

    Relacion.add_single_mapping(
        socio_id=banco_pampa.socio_id,
        tabla="conceptos",
        id_local=conc_imp_debito.id,
        id_foraneo="IMP. DEBITOS Y CRED",
        db=db_session,
    )
    pampa_csv = (
        "Fecha;Concepto;Comprobante;Importe\n"
        "01/09/2026;IMP. DEBITOS Y CRED;555;$ -400,00\n"
        "01/09/2026;TRANSFERENCIA RECIBIDA;556;$ 5.000,00\n"
    )
    pampa_import(io.StringIO(pampa_csv), cuenta_pampa.id)
    mov_p1 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_pampa.id, nro_comprobante="555").first()
    mov_p2 = db_session.query(Movimiento).filter_by(cuenta_id=cuenta_pampa.id, nro_comprobante="556").first()
    assert mov_p1.concepto_id == conc_imp_debito.id
    assert mov_p2.concepto.name == "INGRESO NO CLASIFICADO"

    # 5. Eliminar un Socio Comercial vinculado a un banco debe desvincular el banco sin error de FK
    res_del = delete_aux_record("socios", socio_bica.id, db=db_session)
    assert res_del["status"] == "success"
    db_session.refresh(banco_bica)
    assert banco_bica.socio_id is None
    assert db_session.query(SocioComercial).filter_by(id=socio_bica.id).first() is None

