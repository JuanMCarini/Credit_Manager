from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.connection import get_db
from src.database.models.creditos.cobranzas import LiquidacionCuotaCedida
from src.database.models import SocioComercial, Cartera, TipoOperacionCartera
from src.api.schemas.liquidaciones import (
    LiquidacionResponse,
    LiquidacionProcessRequest,
    LiquidacionPreviewResponse,
    CompradorResponse
)
from src.logic.creditos.settlements import SettlementManager
import math

router = APIRouter(prefix="/api/v1/liquidaciones", tags=["liquidaciones"])

@router.get("", response_model=List[LiquidacionResponse])
def listar_liquidaciones(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    liquidaciones = db.query(LiquidacionCuotaCedida).options(joinedload(LiquidacionCuotaCedida.cuota)).all()
    
    res = []
    for l in liquidaciones:
        res.append({
            "id": l.id,
            "proceso_id": l.proceso_id,
            "cuota_id": l.cuota_id,
            "cartera_id": l.cartera_id,
            "cobranza_id": l.cobranza_id,
            "tipo_liquidacion": getattr(l.tipo_liquidacion, "value", str(l.tipo_liquidacion)),
            "credito_id": l.cuota.credito_id if l.cuota else None,
            "nro_cuota": l.cuota.nro_cuota if l.cuota else None,
            "fecha_vencimiento": l.cuota.fecha_vencimiento if l.cuota else None,
            "capital": l.capital,
            "interes": l.interes,
            "iva": l.iva,
            "importe_total": l.importe_total,
            "fecha_pago": l.fecha_pago,
            "cancelada": l.cancelada
        })
    return res

@router.get("/compradores", response_model=List[CompradorResponse])
def listar_compradores(db: Session = Depends(get_db)):
    compradores = (
        db.query(SocioComercial)
        .join(Cartera, SocioComercial.id == Cartera.socio_id)
        .filter(Cartera.tipo_operacion == TipoOperacionCartera.VENTA)
        .distinct()
        .all()
    )
    return compradores

@router.post("/preview", response_model=List[LiquidacionPreviewResponse])
def preview_liquidaciones(req: LiquidacionProcessRequest, db: Session = Depends(get_db)):
    sm = SettlementManager(db)
    try:
        df_rec, df_s_rec = sm.obtain_settlement_of_transferred_quota(
            id_val=req.id_val,
            identificador=req.identificador,
            fecha=req.fecha_corte,
            fecha_vencimiento_desde=req.fecha_vencimiento_desde,
            fecha_vencimiento_hasta=req.fecha_vencimiento_hasta,
            con_recurso=req.con_recurso
        )
        sm.settlements_resource(df_rec)
        sm.settlements_s_resource(df_s_rec, procesos_cobranza_id=req.procesos_cobranza_id)
        
        df_settlements = sm.settlements
        if df_settlements is None or df_settlements.empty:
            return []
            
        records = df_settlements.to_dict(orient="records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and math.isnan(v):
                    r[k] = None
                # Enums need to be converted to strings if they are returned as enum objects
                if hasattr(v, "value"):
                    r[k] = v.value
        return records
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/procesar")
def procesar_liquidaciones(req: LiquidacionProcessRequest, db: Session = Depends(get_db)):
    sm = SettlementManager(db)
    try:
        df_rec, df_s_rec = sm.obtain_settlement_of_transferred_quota(
            id_val=req.id_val,
            identificador=req.identificador,
            fecha=req.fecha_corte,
            fecha_vencimiento_desde=req.fecha_vencimiento_desde,
            fecha_vencimiento_hasta=req.fecha_vencimiento_hasta,
            con_recurso=req.con_recurso
        )
        sm.settlements_resource(df_rec)
        sm.settlements_s_resource(df_s_rec, procesos_cobranza_id=req.procesos_cobranza_id)
        
        sm.execute_settlements(fecha_pago=None, cancelada=False)
        return {"status": "success", "message": "Liquidaciones procesadas exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
