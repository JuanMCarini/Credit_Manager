from datetime import date
import logging
from typing import Any
from sqlalchemy.orm import Session
from src.database.models.creditos.cobranzas import Cobranza
from src.database.models.creditos.facturacion import Factura
from src.services.arca_service import ArcaService, _clean_cuit

logger = logging.getLogger(__name__)


def procesar_facturacion_pendiente(
    db: Session,
    cobranza_ids: list[int] | None = None,
    fecha_emision: date | None = None,
    punto_venta: int | None = None,
    tipo_comprobante: int | None = None,
    retornar_detalle: bool = False,
) -> int | dict[str, Any]:
    """
    Busca todas las cobranzas que tienen facturada=False y emite la
    factura correspondiente en ARCA respetando el entorno configurado (mock,
    homologacion o produccion).
    Realiza commit individual por cada comprobante autorizado en ARCA para
    evitar perder CAEs otorgados si un ítem posterior del lote falla.
    """
    arca_service = ArcaService()
    cfg = arca_service.config
    pv_eff = (
        int(punto_venta)
        if punto_venta is not None
        else int(cfg.get("punto_venta_default", 1) or 1)
    )
    if tipo_comprobante is not None:
        tipo_eff = int(tipo_comprobante)
    else:
        cond_emisor = cfg.get("condicion_iva_emisor", "RESPONSABLE_INSCRIPTO")
        tipo_eff = 11 if cond_emisor in ("MONOTRIBUTISTA", "EXENTO") else 6

    query = db.query(Cobranza).filter(Cobranza.facturada == False)
    if cobranza_ids is not None:
        if not cobranza_ids:
            if retornar_detalle:
                return {
                    "procesadas": 0,
                    "emitidas": [],
                    "errores": [],
                    "environment": arca_service.environment,
                    "punto_venta": pv_eff,
                    "tipo_comprobante": tipo_eff,
                }
            return 0
        query = query.filter(Cobranza.id.in_(cobranza_ids))

    cobranzas_pendientes = query.all()

    if not cobranzas_pendientes:
        logger.info("No hay cobranzas pendientes de facturar.")
        if retornar_detalle:
            return {
                "procesadas": 0,
                "emitidas": [],
                "errores": [],
                "environment": arca_service.environment,
                "punto_venta": pv_eff,
                "tipo_comprobante": tipo_eff,
            }
        return 0

    facturadas = 0
    emitidas_list: list[dict[str, Any]] = []
    errores_list: list[dict[str, Any]] = []

    for cobranza in cobranzas_pendientes:
        try:
            cuit_cliente = None
            razon_social_receptor = "Consumidor Final"
            domicilio_receptor = None
            provincia_id = None

            if cobranza.cuota and cobranza.cuota.credito and cobranza.cuota.credito.cliente:
                cli = cobranza.cuota.credito.cliente
                cuit_cliente = cli.cuil
                razon_social_receptor = f"{cli.apellido}, {cli.nombre}"
                provincia_id = cli.id_provincia
                if cli.calle:
                    domicilio_receptor = (
                        f"{cli.calle} {cli.calle_nro or ''}, {cli.localidad or ''}".strip(", ")
                    )

            clean_doc = _clean_cuit(cuit_cliente)
            if len(clean_doc) == 11:
                tipo_doc_rec = "CUIL"
            elif len(clean_doc) >= 7:
                tipo_doc_rec = "DNI"
            else:
                tipo_doc_rec = "CF"

            capital_val = round(float(cobranza.capital or 0.0), 2)
            interes_val = round(float(cobranza.interes or 0.0), 2)
            iva_val = round(float(cobranza.iva or 0.0), 2)
            total_val = round(float(cobranza.importe_total or 0.0), 2)

            res = arca_service.emitir_factura(
                punto_venta=pv_eff,
                tipo_comprobante=tipo_eff,
                importe_total=total_val,
                cuit_cliente=clean_doc or None,
                fecha_emision=fecha_emision,
                db=db,
                concepto_arca=2,
                tipo_doc_receptor=tipo_doc_rec,
                condicion_iva_receptor="Consumidor Final",
                condicion_iva_receptor_id=5,
                importe_no_gravado=capital_val,
                importe_exento=0.0,
                neto_gravado_21=interes_val,
                iva_21=iva_val,
            )

            nueva_factura = Factura(
                cobranza_id=cobranza.id,
                origen="COBRANZA",
                punto_venta=res["punto_venta"],
                tipo_comprobante=res["tipo_comprobante"],
                nro_comprobante=res["nro_comprobante"],
                fecha_emision=res["fecha_emision"],
                concepto_arca=2,
                tipo_doc_receptor=tipo_doc_rec,
                cuit_cliente=res["cuit_cliente"],
                razon_social_receptor=razon_social_receptor,
                domicilio_receptor=domicilio_receptor,
                condicion_iva_receptor="Consumidor Final",
                condicion_iva_receptor_id=5,
                provincia_id=provincia_id,
                importe_no_gravado=capital_val,
                importe_exento=0.0,
                neto_gravado_0=0.0,
                neto_gravado_21=interes_val,
                neto_gravado_105=0.0,
                neto_gravado_27=0.0,
                iva_21=iva_val,
                iva_105=0.0,
                iva_27=0.0,
                percepcion_iva=0.0,
                percepcion_iibb=0.0,
                otros_impuestos=0.0,
                importe_total=res["importe_total"],
                cae=res["cae"],
                vencimiento_cae=res["vencimiento_cae"],
                estado_arca="MOCK"
                if arca_service.use_mock
                else f"AUTORIZADA_{arca_service.environment.upper()}",
            )
            db.add(nueva_factura)
            cobranza.facturada = True
            db.commit()
            db.refresh(nueva_factura)
            facturadas += 1
            emitidas_list.append(
                {
                    "factura_id": nueva_factura.id,
                    "cobranza_id": cobranza.id,
                    "comprobante": f"{nueva_factura.punto_venta:04d}-{nueva_factura.nro_comprobante:08d}",
                    "cae": nueva_factura.cae,
                    "importe_total": float(nueva_factura.importe_total),
                }
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error facturando cobranza {cobranza.id}: {str(e)}")
            errores_list.append(
                {
                    "cobranza_id": cobranza.id,
                    "error": str(e),
                }
            )
            continue

    logger.info(
        f"Se facturaron exitosamente {facturadas} cobranzas (errores: {len(errores_list)})."
    )

    if retornar_detalle:
        return {
            "procesadas": facturadas,
            "emitidas": emitidas_list,
            "errores": errores_list,
            "environment": arca_service.environment,
            "punto_venta": pv_eff,
            "tipo_comprobante": tipo_eff,
        }

    return facturadas
