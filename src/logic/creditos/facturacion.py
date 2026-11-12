from datetime import date
import logging
from sqlalchemy.orm import Session
from src.database.models.creditos.cobranzas import Cobranza
from src.database.models.creditos.facturacion import Factura
from src.services.arca_service import ArcaService

logger = logging.getLogger(__name__)


def procesar_facturacion_pendiente(
    db: Session,
    cobranza_ids: list[int] | None = None,
    fecha_emision: date | None = None,
    punto_venta: int = 1,
    tipo_comprobante: int = 6,
):
    """
    Busca todas las cobranzas que tienen facturada=False y emite la
    factura correspondiente en ARCA.
    Si se pasa cobranza_ids, solo factura esas cobranzas específicas.
    tipo_comprobante=6 corresponde a Factura B.
    """
    query = db.query(Cobranza).filter(Cobranza.facturada == False)
    if cobranza_ids is not None:
        if not cobranza_ids:
            return 0
        query = query.filter(Cobranza.id.in_(cobranza_ids))

    cobranzas_pendientes = query.all()

    if not cobranzas_pendientes:
        logger.info("No hay cobranzas pendientes de facturar.")
        return 0

    arca_service = ArcaService(use_mock=True)
    facturadas = 0

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
                    domicilio_receptor = f"{cli.calle} {cli.calle_nro or ''}, {cli.localidad or ''}".strip(", ")

            res = arca_service.emitir_factura(
                punto_venta=punto_venta,
                tipo_comprobante=tipo_comprobante,
                importe_total=float(cobranza.importe_total),
                cuit_cliente=cuit_cliente,
                fecha_emision=fecha_emision,
                db=db,
            )

            capital_val = float(cobranza.capital or 0.0)
            interes_val = float(cobranza.interes or 0.0)
            iva_val = float(cobranza.iva or 0.0)

            nueva_factura = Factura(
                cobranza_id=cobranza.id,
                origen="COBRANZA",
                punto_venta=res["punto_venta"],
                tipo_comprobante=res["tipo_comprobante"],
                nro_comprobante=res["nro_comprobante"],
                fecha_emision=res["fecha_emision"],
                concepto_arca=2,
                tipo_doc_receptor="CUIL" if cuit_cliente else "CF",
                cuit_cliente=res["cuit_cliente"],
                razon_social_receptor=razon_social_receptor,
                domicilio_receptor=domicilio_receptor,
                condicion_iva_receptor="Consumidor Final",
                provincia_id=provincia_id,
                importe_no_gravado=capital_val,
                importe_exento=0.0,
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
            )
            db.add(nueva_factura)
            cobranza.facturada = True
            db.flush()
            facturadas += 1

        except Exception as e:
            logger.error(f"Error facturando cobranza {cobranza.id}: {str(e)}")
            continue

    try:
        db.commit()
        logger.info(f"Se facturaron exitosamente {facturadas} cobranzas.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al hacer commit de la facturación: {str(e)}")
        raise e

    return facturadas
