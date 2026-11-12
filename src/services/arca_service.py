import logging
import random
from datetime import date, datetime, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ArcaService:
    """
    Servicio de integración con ARCA/AFIP (WSFEv1) usando afip.py.
    Soporta todos los tipos de comprobantes electrónicos (Facturas A/B/C/M/E,
    Notas de Débito/Crédito, Recibos y Facturas de Crédito Electrónicas MiPyMEs).
    """

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def obtener_proximo_numero(self, db, punto_venta: int, tipo_comprobante: int) -> int:
        from src.database.models.creditos.facturacion import Factura

        max_nro = (
            db.query(func.max(Factura.nro_comprobante))
            .filter(
                Factura.punto_venta == int(punto_venta),
                Factura.tipo_comprobante == int(tipo_comprobante),
            )
            .scalar()
        )
        return int(max_nro or 0) + 1

    def emitir_factura(
        self,
        punto_venta: int,
        tipo_comprobante: int,
        importe_total: float,
        cuit_cliente: str | None = None,
        fecha_emision: date | None = None,
        ultimo_nro: int | None = None,
        db=None,
        **kwargs,
    ) -> dict:
        """
        Emite un comprobante electrónico en ARCA y retorna el número correlativo,
        CAE y fecha de vencimiento de CAE.
        """
        if self.use_mock:
            fecha_eff = fecha_emision or datetime.now().date()
            if ultimo_nro is not None:
                nro_comprobante = int(ultimo_nro) + 1
            elif db is not None:
                nro_comprobante = self.obtener_proximo_numero(db, punto_venta, tipo_comprobante)
            else:
                nro_comprobante = random.randint(1000, 9999)

            logger.info(
                f"[ARCA MOCK] Emitiendo comprobante Tipo {tipo_comprobante} "
                f"PV {punto_venta:04d}-{nro_comprobante:08d} por ${float(importe_total):,.2f}"
            )

            cae = f"7{random.randint(1000000000000, 9999999999999)}"
            vencimiento_cae = fecha_eff + timedelta(days=10)

            return {
                "nro_comprobante": nro_comprobante,
                "cae": cae,
                "vencimiento_cae": vencimiento_cae,
                "fecha_emision": fecha_eff,
                "importe_total": round(float(importe_total), 2),
                "punto_venta": int(punto_venta),
                "tipo_comprobante": int(tipo_comprobante),
                "cuit_cliente": cuit_cliente,
            }

        raise NotImplementedError("Modo producción no configurado. Faltan certificados WSAA/WSFEv1.")
