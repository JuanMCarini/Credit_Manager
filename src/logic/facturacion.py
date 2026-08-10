from sqlalchemy.orm import Session
from src.database.models.cobranzas import Cobranza
from src.database.models.facturacion import Factura
from src.services.arca_service import ArcaService
import logging

logger = logging.getLogger(__name__)

from datetime import date

def procesar_facturacion_pendiente(db: Session, cobranza_ids: list[int] = None, fecha_emision: date = None, punto_venta: int = 1, tipo_comprobante: int = 6):
    """
    Busca todas las cobranzas que tienen facturada=False y emite la 
    factura correspondiente en ARCA (modo simulador activo).
    Si se pasa cobranza_ids, solo factura esas cobranzas específicas.
    tipo_comprobante=6 suele ser Factura B.
    """
    query = db.query(Cobranza).filter(Cobranza.facturada == False)
    if cobranza_ids is not None:
        if not cobranza_ids:
            return 0  # Lista vacía = nada que procesar
        query = query.filter(Cobranza.id.in_(cobranza_ids))
        
    cobranzas_pendientes = query.all()
    
    if not cobranzas_pendientes:
        logger.info("No hay cobranzas pendientes de facturar.")
        return 0
        
    arca_service = ArcaService(use_mock=True)
    facturadas = 0
    
    for cobranza in cobranzas_pendientes:
        try:
            # Obtener el CUIT del cliente si se puede (opcional para consumidor final de bajo monto)
            cuit_cliente = None
            if cobranza.cuota and cobranza.cuota.credito and cobranza.cuota.credito.cliente:
                cuit_cliente = cobranza.cuota.credito.cliente.cuil
            
            # Llamar al servicio ARCA
            res = arca_service.emitir_factura(
                punto_venta=punto_venta,
                tipo_comprobante=tipo_comprobante,
                importe_total=float(cobranza.importe_total),
                cuit_cliente=cuit_cliente,
                fecha_emision=fecha_emision
            )
            
            # Crear y guardar la factura en DB
            nueva_factura = Factura(
                cobranza_id=cobranza.id,
                punto_venta=res["punto_venta"],
                tipo_comprobante=res["tipo_comprobante"],
                nro_comprobante=res["nro_comprobante"],
                fecha_emision=res["fecha_emision"],
                importe_total=res["importe_total"],
                cae=res["cae"],
                vencimiento_cae=res["vencimiento_cae"],
                cuit_cliente=res["cuit_cliente"]
            )
            db.add(nueva_factura)
            
            # Marcar la cobranza como facturada
            cobranza.facturada = True
            
            # Hacemos flush para evitar ids duplicados en el contexto (opcional)
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