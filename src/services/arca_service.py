import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ArcaService:
    """
    Servicio de integración con ARCA/AFIP usando afip.py
    Actualmente en modo mock (simulado) según requerimiento.
    """
    
    def __init__(self, use_mock=True):
        self.use_mock = use_mock
        # Aquí iría la inicialización real:
        # from afip import Afip
        # self.afip = Afip({'CUIT': 30000000000, 'cert': 'cert.crt', 'key': 'key.key', 'production': False})
        
    def emitir_factura(self, punto_venta: int, tipo_comprobante: int, importe_total: float, cuit_cliente: str = None) -> dict:
        """
        Emite una factura electrónica en ARCA.
        """
        if self.use_mock:
            logger.info(f"[ARCA MOCK] Emitiendo comprobante Tipo {tipo_comprobante} PV {punto_venta} por ${importe_total}")
            
            # Simulamos el Nro de Comprobante (auto-incremental por PV)
            nro_comprobante = random.randint(1000, 9999)
            
            # Simulamos el CAE y Vencimiento
            cae = f"7{random.randint(1000000000000, 9999999999999)}"
            vencimiento_cae = (datetime.now() + timedelta(days=10)).date()
            
            return {
                "nro_comprobante": nro_comprobante,
                "cae": cae,
                "vencimiento_cae": vencimiento_cae,
                "fecha_emision": datetime.now().date(),
                "importe_total": importe_total,
                "punto_venta": punto_venta,
                "tipo_comprobante": tipo_comprobante,
                "cuit_cliente": cuit_cliente
            }
            
        else:
            # Lógica real usando self.afip.ElectronicBilling.createVoucher(...)
            raise NotImplementedError("Modo producción no configurado. Faltan certificados.")
