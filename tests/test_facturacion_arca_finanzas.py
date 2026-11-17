from datetime import date
import io
import pandas as pd
import pytest
from fastapi import HTTPException

from src.database.models import Provincia, SocioComercial
from src.api.routes.facturacion import (
    EmitirFacturaIndividualRequest,
    ItemFacturaInput,
    emitir_factura_individual,
    get_facturas_emitidas,
    get_receptores_facturacion,
    get_tipos_comprobante,
    descargar_pdf_individual,
    descargar_libro_iva,
)
from src.api.routes.posicion_iva import calcular_posicion as calcular_posicion_iva
from src.api.routes.posicion_iibb import calcular_posicion as calcular_posicion_iibb


def test_catalogo_tipos_y_receptores(db_session):
    prov = Provincia(nombre="Santa Fe")
    socio = SocioComercial(
        razon_social="Inversora Litoral SA",
        cuit="30712345678",
        domicilio_legal="San Martín 1200, Rosario",
    )
    db_session.add_all([prov, socio])
    db_session.commit()

    tipos = get_tipos_comprobante()
    codigos = {t["codigo"] for t in tipos}
    # Verificar presencia de Facturas A, B, C, M, E, Notas de Crédito/Débito, Recibos y FCE MiPyME
    for esperado in (1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 15, 19, 20, 21, 51, 52, 53, 54, 201, 202, 203, 206, 211):
        assert esperado in codigos

    rec_data = get_receptores_facturacion(db=db_session)
    assert any(r["nro_doc"] == "30712345678" for r in rec_data["receptores"])
    assert any(p["nombre"] == "Santa Fe" for p in rec_data["provincias"])


def test_emision_individual_multitipo_correlatividad_y_validaciones(db_session):
    prov = Provincia(nombre="Córdoba")
    db_session.add(prov)
    db_session.commit()

    # 1. Factura A sin CUIT válido de 11 dígitos debe rechazarse
    with pytest.raises(HTTPException) as exc_cuit:
        emitir_factura_individual(
            EmitirFacturaIndividualRequest(
                punto_venta=2,
                tipo_comprobante=1,
                cuit_cliente="12345",
                razon_social_receptor="Empresa Inválida",
                items=[ItemFacturaInput(descripcion="Asesoramiento", cantidad=1, precio_unitario=10000, alicuota_iva="21")],
            ),
            db=db_session,
        )
    assert exc_cuit.value.status_code == 400

    # 2. Nota de Crédito sin comprobante asociado debe rechazarse
    with pytest.raises(HTTPException) as exc_nc:
        emitir_factura_individual(
            EmitirFacturaIndividualRequest(
                punto_venta=2,
                tipo_comprobante=3,
                cuit_cliente="30711122233",
                razon_social_receptor="Cliente RI SA",
                items=[ItemFacturaInput(descripcion="Anulación", cantidad=1, precio_unitario=5000, alicuota_iva="21")],
            ),
            db=db_session,
        )
    assert exc_nc.value.status_code == 400

    # 3. Emitir dos Facturas A seguidas en PV 2 -> correlatividad 1 y 2
    f1 = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=1,
            fecha_emision=date(2026, 6, 10),
            cuit_cliente="30711122233",
            razon_social_receptor="Cliente RI SA",
            condicion_iva_receptor="Responsable Inscripto",
            provincia_id=prov.id,
            items=[
                ItemFacturaInput(descripcion="Comisión estructuración", cantidad=1, precio_unitario=100000, alicuota_iva="21"),
                ItemFacturaInput(descripcion="Servicio técnico", cantidad=2, precio_unitario=20000, alicuota_iva="10.5"),
            ],
        ),
        db=db_session,
    )
    assert f1["nro_comprobante"] == 1
    assert f1["letra"] == "A"
    # Neto = 100.000 + 40.000 = 140.000 | IVA = 21.000 + 4.200 = 25.200 | Total = 165.200
    assert f1["importe_total"] == pytest.approx(165200.0)

    f2 = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=1,
            fecha_emision=date(2026, 6, 11),
            cuit_cliente="30711122233",
            razon_social_receptor="Cliente RI SA",
            condicion_iva_receptor="Responsable Inscripto",
            provincia_id=prov.id,
            items=[
                ItemFacturaInput(descripcion="Gestión de cartera", cantidad=1, precio_unitario=50000, alicuota_iva="21"),
            ],
        ),
        db=db_session,
    )
    assert f2["nro_comprobante"] == 2
    assert f2["importe_total"] == pytest.approx(60500.0)

    # 4. Emitir Factura B (6), Factura C (11), Factura M (51), Factura E (19) y FCE MiPyME A (201)
    fb = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=6,
            fecha_emision=date(2026, 6, 12),
            tipo_doc_receptor="DNI",
            cuit_cliente="30111222",
            razon_social_receptor="Juan Consumidor",
            condicion_iva_receptor="Consumidor Final",
            provincia_id=prov.id,
            items=[ItemFacturaInput(descripcion="Cargo administrativo", cantidad=1, precio_unitario=12100, alicuota_iva="21")],
        ),
        db=db_session,
    )
    assert fb["letra"] == "B"
    assert fb["nro_comprobante"] == 1
    assert fb["importe_total"] == pytest.approx(12100.0)

    fc = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=11,
            fecha_emision=date(2026, 6, 12),
            razon_social_receptor="Monotributista Receptor",
            items=[ItemFacturaInput(descripcion="Servicio exento C", cantidad=1, precio_unitario=15000, alicuota_iva="EXENTO")],
        ),
        db=db_session,
    )
    assert fc["letra"] == "C"
    assert fc["importe_total"] == pytest.approx(15000.0)

    fm = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=51,
            fecha_emision=date(2026, 6, 12),
            cuit_cliente="30799988877",
            razon_social_receptor="Receptor Clase M SA",
            items=[ItemFacturaInput(descripcion="Honorarios M", cantidad=1, precio_unitario=10000, alicuota_iva="21")],
        ),
        db=db_session,
    )
    assert fm["letra"] == "M"
    assert fm["importe_total"] == pytest.approx(12100.0)

    fe = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=19,
            fecha_emision=date(2026, 6, 12),
            cuit_cliente="55000000018",
            razon_social_receptor="Foreign Corp LLC",
            condicion_iva_receptor="Cliente del Exterior",
            items=[ItemFacturaInput(descripcion="Exportación de software", cantidad=1, precio_unitario=25000, alicuota_iva="EXENTO")],
        ),
        db=db_session,
    )
    assert fe["letra"] == "E"
    assert fe["importe_total"] == pytest.approx(25000.0)

    fce = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=2,
            tipo_comprobante=201,
            fecha_emision=date(2026, 6, 12),
            cuit_cliente="30711122233",
            razon_social_receptor="Gran Empresa SA",
            cbu_emisor="0720000720000000123456",
            items=[ItemFacturaInput(descripcion="Consultoría FCE MiPyME", cantidad=1, precio_unitario=200000, alicuota_iva="21")],
        ),
        db=db_session,
    )
    assert fce["tipo_comprobante"] == 201
    assert fce["importe_total"] == pytest.approx(242000.0)


def test_impacto_iva_iibb_libro_iva_y_pdf_con_nota_de_credito(db_session):
    prov_ba = Provincia(nombre="Buenos Aires")
    db_session.add(prov_ba)
    db_session.commit()

    # 1. Emitir Factura A en Julio 2026: Neto = $100.000, IVA 21% = $21.000, Total = $121.000
    fac_a = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=5,
            tipo_comprobante=1,
            fecha_emision=date(2026, 7, 15),
            cuit_cliente="30744455566",
            razon_social_receptor="Fiduciaria del Sur SA",
            condicion_iva_receptor="Responsable Inscripto",
            provincia_id=prov_ba.id,
            items=[
                ItemFacturaInput(
                    descripcion="Comisión de administración financiera",
                    cantidad=1,
                    precio_unitario=100000.0,
                    alicuota_iva="21",
                )
            ],
        ),
        db=db_session,
    )

    # 2. Emitir Nota de Crédito A (código 3) vinculada a fac_a por Neto = $30.000, IVA 21% = $6.300, Total = $36.300
    nc_a = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=5,
            tipo_comprobante=3,
            fecha_emision=date(2026, 7, 20),
            cuit_cliente="30744455566",
            razon_social_receptor="Fiduciaria del Sur SA",
            condicion_iva_receptor="Responsable Inscripto",
            provincia_id=prov_ba.id,
            comprobante_asociado_id=fac_a["id"],
            items=[
                ItemFacturaInput(
                    descripcion="Bonificación sobre comisión de administración",
                    cantidad=1,
                    precio_unitario=30000.0,
                    alicuota_iva="21",
                )
            ],
        ),
        db=db_session,
    )

    # 3. Verificar listado de emitidas y KPIs netos ($121.000 - $36.300 = $84.700; IVA $21.000 - $6.300 = $14.700)
    listado = get_facturas_emitidas(
        skip=0,
        limit=100,
        fecha_desde=date(2026, 7, 1),
        fecha_hasta=date(2026, 7, 31),
        origen="FINANZAS",
        punto_venta=None,
        tipo_comprobante=None,
        search=None,
        db=db_session,
    )
    assert listado["total"] == 2
    assert listado["kpis"]["total_facturado_neto"] == pytest.approx(84700.0)
    assert listado["kpis"]["total_iva_debito"] == pytest.approx(14700.0)
    assert listado["kpis"]["total_notas_credito"] == pytest.approx(36300.0)

    # 4. Verificar impacto en Posición de IVA (Julio 2026): IVA Ventas = $21.000 - $6.300 = $14.700
    pos_iva = calcular_posicion_iva(anio=2026, mes=7, db=db_session)
    assert pos_iva["iva_ventas"] == pytest.approx(14700.0)

    # 5. Verificar impacto en Posición de IIBB (Julio 2026): Base neta Buenos Aires = $100.000 - $30.000 = $70.000
    pos_iibb = calcular_posicion_iibb(anio=2026, mes=7, db=db_session)
    prov_entry = next(
        (v for v in pos_iibb["ventas_por_provincia"] if v["provincia"] == "Buenos Aires"),
        None,
    )
    assert prov_entry is not None
    assert prov_entry["neto"] == pytest.approx(70000.0)

    # 6. Verificar Libro IVA Ventas Excel (Nota de Crédito con signo negativo)
    res_libro = descargar_libro_iva(
        fecha_desde=date(2026, 7, 1),
        fecha_hasta=date(2026, 7, 31),
        db=db_session,
    )
    df_libro = pd.read_excel(io.BytesIO(res_libro.body))
    assert len(df_libro) == 2
    row_nc = df_libro[df_libro["Tipo Comprobante"] == "Nota de Crédito A"].iloc[0]
    assert float(row_nc["GRAVADO"]) == pytest.approx(-30000.0)
    assert float(row_nc["IVA"]) == pytest.approx(-6300.0)
    assert float(row_nc["Importe Total"]) == pytest.approx(-36300.0)

    # 7. Verificar descarga de PDF individual (firma %PDF-)
    res_pdf = descargar_pdf_individual(factura_id=fac_a["id"], db=db_session)
    assert res_pdf.media_type == "application/pdf"
    assert res_pdf.body.startswith(b"%PDF-")

    res_pdf_nc = descargar_pdf_individual(factura_id=nc_a["id"], db=db_session)
    assert res_pdf_nc.body.startswith(b"%PDF-")

    # 8. Verificar estado de NC parcial en el listado y bloqueo cuando se supera el saldo o se anula el 100%
    fac_item_parcial = next(it for it in listado["items"] if it["id"] == fac_a["id"])
    assert fac_item_parcial["tiene_nc_parcial"] is True
    assert fac_item_parcial["anulada_por_nc"] is False
    assert fac_item_parcial["saldo_pendiente_nc"] == pytest.approx(84700.0)

    # Intentar emitir una NC que supere el saldo restante ($84.700) debe fallar con 400
    with pytest.raises(HTTPException) as exc_exceso:
        emitir_factura_individual(
            EmitirFacturaIndividualRequest(
                punto_venta=5,
                tipo_comprobante=3,
                fecha_emision=date(2026, 7, 22),
                cuit_cliente="30744455566",
                razon_social_receptor="Fiduciaria del Sur SA",
                comprobante_asociado_id=fac_a["id"],
                items=[ItemFacturaInput(descripcion="Exceso NC", cantidad=1, precio_unitario=80000.0, alicuota_iva="21")],
            ),
            db=db_session,
        )
    assert exc_exceso.value.status_code == 400

    # Emitir NC por el saldo exacto restante (Neto $70.000 + IVA $14.700 = $84.700)
    emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=5,
            tipo_comprobante=3,
            fecha_emision=date(2026, 7, 25),
            cuit_cliente="30744455566",
            razon_social_receptor="Fiduciaria del Sur SA",
            comprobante_asociado_id=fac_a["id"],
            items=[ItemFacturaInput(descripcion="Anulación saldo restante", cantidad=1, precio_unitario=70000.0, alicuota_iva="21")],
        ),
        db=db_session,
    )

    listado_final = get_facturas_emitidas(
        skip=0,
        limit=100,
        fecha_desde=date(2026, 7, 1),
        fecha_hasta=date(2026, 7, 31),
        origen="FINANZAS",
        punto_venta=None,
        tipo_comprobante=None,
        search=None,
        db=db_session,
    )
    fac_item_final = next(it for it in listado_final["items"] if it["id"] == fac_a["id"])
    assert fac_item_final["anulada_por_nc"] is True
    assert fac_item_final["tiene_nc_parcial"] is False
    assert fac_item_final["saldo_pendiente_nc"] == pytest.approx(0.0)

    # Intentar emitir una nueva NC sobre la factura ya anulada al 100% debe fallar con 400
    with pytest.raises(HTTPException) as exc_anulada:
        emitir_factura_individual(
            EmitirFacturaIndividualRequest(
                punto_venta=5,
                tipo_comprobante=3,
                fecha_emision=date(2026, 7, 26),
                cuit_cliente="30744455566",
                razon_social_receptor="Fiduciaria del Sur SA",
                comprobante_asociado_id=fac_a["id"],
                items=[ItemFacturaInput(descripcion="NC extra", cantidad=1, precio_unitario=100.0, alicuota_iva="21")],
            ),
            db=db_session,
        )
    assert exc_anulada.value.status_code == 400


def test_factura_b_redondeo_exacto_y_consulta_padron(db_session):
    """
    Verifica que en Factura B con precio final $100.00 (IVA 21% incluido):
      - neto_21 = $82.64
      - iva_21 = $17.36 (por diferencia exacta bruto - neto)
      - importe_total = $100.00 (sin desfase de $0.01)
    Y verifica el endpoint de consulta de CUIT en padrón con sugerencia de provincia.
    """
    from src.api.routes.facturacion import consultar_cuit_padron_arca
    import asyncio

    prov_caba = Provincia(nombre="Capital Federal")
    db_session.add(prov_caba)
    db_session.commit()

    fb_100 = emitir_factura_individual(
        EmitirFacturaIndividualRequest(
            punto_venta=1,
            tipo_comprobante=6,
            fecha_emision=date(2026, 8, 10),
            tipo_doc_receptor="DNI",
            cuit_cliente="28999111",
            razon_social_receptor="Consumidor Redondeo",
            condicion_iva_receptor="Consumidor Final",
            items=[
                ItemFacturaInput(
                    descripcion="Servicio redondo $100 final",
                    cantidad=1,
                    precio_unitario=100.0,
                    alicuota_iva="21",
                )
            ],
        ),
        db=db_session,
    )
    assert fb_100["neto_gravado_21"] == pytest.approx(82.64)
    assert fb_100["iva_21"] == pytest.approx(17.36)
    assert fb_100["importe_total"] == pytest.approx(100.00)

    padron_res = consultar_cuit_padron_arca("30-71234567-8", db=db_session)
    assert padron_res["cuit"] == "30712345678"
    assert padron_res["condicion_iva_receptor_id"] == 1
    assert padron_res["provincia_id_sugerida"] == prov_caba.id


def test_facturacion_masiva_cobranzas_repregunta_entorno_real(db_session, tmp_path, monkeypatch):
    """
    Verifica que POST /api/v1/facturacion/procesar exija confirmar_real=True
    cuando ARCA está configurado en homologacion o produccion.
    """
    import src.services.arca_service as arca_service
    from src.api.routes.facturacion import ProcesarRequest, procesar_facturacion

    certs_dir = tmp_path / "certs_batch" / "arca"
    monkeypatch.setattr(arca_service, "ARCA_CERTS_DIR", certs_dir)
    monkeypatch.setattr(arca_service, "ARCA_CONFIG_PATH", certs_dir / "arca_config.json")

    arca_service.save_arca_config(
        {
            "environment": "homologacion",
            "cuit": "30712345678",
            "punto_venta_default": 2,
        }
    )

    with pytest.raises(HTTPException) as exc_conf:
        procesar_facturacion(
            ProcesarRequest(
                fecha_desde=date(2026, 8, 1),
                fecha_hasta=date(2026, 8, 31),
                confirmar_real=False,
            ),
            db=db_session,
        )
    assert exc_conf.value.status_code == 400
    assert "confirmar explícitamente" in exc_conf.value.detail.lower()


def test_separacion_facturas_mock_en_entorno_real(db_session, tmp_path, monkeypatch):
    """
    Verifica que cuando el entorno ARCA es real (homologacion/produccion), las facturas
    con estado_arca='MOCK' no contaminen get_ultima_fecha_factura, Libro IVA, Posición IVA,
    Posición IIBB ni get_facturas_emitidas en producción.
    """
    import src.services.arca_service as arca_service
    from src.database.models.creditos.facturacion import Factura
    from src.api.routes.facturacion import get_ultima_fecha_factura

    certs_dir = tmp_path / "certs_sep" / "arca"
    monkeypatch.setattr(arca_service, "ARCA_CERTS_DIR", certs_dir)
    monkeypatch.setattr(arca_service, "ARCA_CONFIG_PATH", certs_dir / "arca_config.json")

    prov = Provincia(nombre="Mendoza")
    db_session.add(prov)
    db_session.commit()

    f_mock = Factura(
        origen="FINANZAS",
        punto_venta=1,
        tipo_comprobante=1,
        nro_comprobante=99,
        fecha_emision=date(2026, 9, 25),
        cuit_cliente="30711122233",
        razon_social_receptor="Mock SA",
        provincia_id=prov.id,
        neto_gravado_21=10000.0,
        iva_21=2100.0,
        importe_total=12100.0,
        cae="70000000000001",
        estado_arca="MOCK",
    )
    f_real = Factura(
        origen="FINANZAS",
        punto_venta=1,
        tipo_comprobante=1,
        nro_comprobante=1,
        fecha_emision=date(2026, 9, 10),
        cuit_cliente="30744455566",
        razon_social_receptor="Real SA",
        provincia_id=prov.id,
        neto_gravado_21=5000.0,
        iva_21=1050.0,
        importe_total=6050.0,
        cae="75111122223333",
        estado_arca="AUTORIZADA_PRODUCCION",
    )
    db_session.add_all([f_mock, f_real])
    db_session.commit()

    arca_service.save_arca_config(
        {"environment": "produccion", "cuit": "30712345678", "punto_venta_default": 1}
    )

    # Última fecha en producción debe ignorar la factura MOCK del 25/09 y devolver 10/09
    ultima = get_ultima_fecha_factura(db=db_session)
    assert ultima["ultima_fecha"] == "2026-09-10"

    # Listado y KPIs en producción excluyen MOCK por defecto
    listado = get_facturas_emitidas(
        skip=0,
        limit=100,
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 30),
        origen="FINANZAS",
        db=db_session,
    )
    assert listado["total"] == 1
    assert listado["items"][0]["razon_social_receptor"] == "Real SA"
    assert listado["kpis"]["total_iva_debito"] == pytest.approx(1050.0)

    # Posición IVA e IIBB también excluyen MOCK
    pos_iva = calcular_posicion_iva(anio=2026, mes=9, db=db_session)
    assert pos_iva["iva_ventas"] == pytest.approx(1050.0)

    pos_iibb = calcular_posicion_iibb(anio=2026, mes=9, db=db_session)
    prov_mza = next(v for v in pos_iibb["ventas_por_provincia"] if v["provincia"] == "Mendoza")
    assert prov_mza["neto"] == pytest.approx(5000.0)

    # Libro IVA Excel excluye MOCK
    res_libro = descargar_libro_iva(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 30),
        db=db_session,
    )
    df_libro = pd.read_excel(io.BytesIO(res_libro.body))
    assert len(df_libro) == 1
    assert df_libro.iloc[0]["Razón Social"] == "Real SA"


def test_circuit_breaker_lote_cobranzas_ante_error_estructural_vs_puntual(
    db_session, dummy_cliente, dummy_cartera, tmp_path, monkeypatch
):
    """
    Verifica que procesar_facturacion_pendiente:
      1. Detenga el lote inmediatamente en el primer fallo ante un error estructural (ej. 502 o código 600).
      2. Continúe procesando el resto del lote ante un error puntual de una cobranza (ej. 400 código 10015).
    """
    import src.services.arca_service as arca_service
    from src.services.arca_service import ArcaService, ArcaServiceError
    from src.database.models import Credito, Cuota, EstadoCuota, TipoCredito, Cobranza, TipoCobranzaEnum
    from src.logic.creditos.facturacion import procesar_facturacion_pendiente

    certs_dir = tmp_path / "certs_cb" / "arca"
    monkeypatch.setattr(arca_service, "ARCA_CERTS_DIR", certs_dir)
    monkeypatch.setattr(arca_service, "ARCA_CONFIG_PATH", certs_dir / "arca_config.json")
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "30712345678", "punto_venta_default": 1})

    credito = Credito(
        cliente_cuil=dummy_cliente.cuil,
        cartera_id=dummy_cartera.id,
        capital=3000.0,
        tna_c_iva=0.5,
        plazo=3,
        fecha_emision=date(2026, 10, 1),
        tipo_credito=TipoCredito.FRANCES,
        dia_vencimiento=10,
    )
    db_session.add(credito)
    db_session.flush()

    cuotas = [
        Cuota(
            credito_id=credito.id,
            nro_cuota=i,
            fecha_vencimiento=date(2026, 10, 10),
            capital=100.0,
            interes=20.0,
            iva=4.20,
            estado=EstadoCuota.CANCELADA,
        )
        for i in (1, 2, 3)
    ]
    db_session.add_all(cuotas)
    db_session.flush()

    cobranzas = [
        Cobranza(
            cuota_id=c.id,
            tipo_cobranza=TipoCobranzaEnum.COMUN,
            capital=100.0,
            interes=20.0,
            iva=4.20,
            fecha=date(2026, 10, 10),
            facturada=False,
        )
        for c in cuotas
    ]
    db_session.add_all(cobranzas)
    db_session.commit()
    cob_ids = [c.id for c in cobranzas]

    # Caso 1: Error estructural (HTTP 502) -> debe abortar en la primera llamada sin intentar las otras 2
    llamadas_estructural = {"count": 0}

    def fake_emitir_estructural(self, **kwargs):
        llamadas_estructural["count"] += 1
        raise ArcaServiceError("Error de red al conectar con WSFEv1", status_http=502)

    monkeypatch.setattr(ArcaService, "emitir_factura", fake_emitir_estructural)
    res_abort = procesar_facturacion_pendiente(
        db_session,
        cobranza_ids=cob_ids,
        fecha_emision=date(2026, 11, 17),
        retornar_detalle=True,
    )
    assert llamadas_estructural["count"] == 1
    assert res_abort["procesadas"] == 0
    assert len(res_abort["errores"]) == 1
    assert res_abort["lote_abortado"] is True
    assert "Error de red" in res_abort["motivo_aborto"]

    # Todas las cobranzas siguen con facturada=False
    assert db_session.query(Cobranza).filter(Cobranza.id.in_(cob_ids), Cobranza.facturada == False).count() == 3

    # Caso 2: Error puntual (400 / código 10015) en la 1ra cobranza -> debe continuar y emitir las 2 restantes
    llamadas_puntual = {"count": 0}

    def fake_emitir_puntual(self, **kwargs):
        llamadas_puntual["count"] += 1
        if llamadas_puntual["count"] == 1:
            raise ArcaServiceError("ARCA rechazó el comprobante: [10015] DocNro inválido", code="10015", status_http=400)
        return {
            "nro_comprobante": llamadas_puntual["count"],
            "cae": f"7500000000000{llamadas_puntual['count']}",
            "vencimiento_cae": date(2026, 11, 27),
            "fecha_emision": date(2026, 11, 17),
            "importe_total": kwargs["importe_total"],
            "punto_venta": kwargs["punto_venta"],
            "tipo_comprobante": kwargs["tipo_comprobante"],
            "cuit_cliente": kwargs.get("cuit_cliente"),
        }

    monkeypatch.setattr(ArcaService, "emitir_factura", fake_emitir_puntual)
    res_cont = procesar_facturacion_pendiente(
        db_session,
        cobranza_ids=cob_ids,
        fecha_emision=date(2026, 11, 17),
        retornar_detalle=True,
    )
    assert llamadas_puntual["count"] == 3
    assert res_cont["procesadas"] == 2
    assert len(res_cont["errores"]) == 1
    assert res_cont["lote_abortado"] is False
    assert res_cont["motivo_aborto"] is None
    assert db_session.query(Cobranza).filter(Cobranza.id.in_(cob_ids), Cobranza.facturada == False).count() == 1




