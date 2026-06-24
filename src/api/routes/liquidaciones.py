from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.connection import get_db
from src.database.models.cobranzas import LiquidacionCuotaCedida
from src.database.models import SocioComercial, Cartera, TipoOperacionCartera
from src.api.schemas.liquidaciones import (
    LiquidacionResponse,
    LiquidacionProcessRequest,
    LiquidacionPreviewResponse,
    CompradorResponse
)
from src.logic.settlements import SettlementManager
import math

router = APIRouter(prefix="/api/v1/liquidaciones", tags=["liquidaciones"])

@router.get("", response_model=List[LiquidacionResponse])
def listar_liquidaciones(db: Session = Depends(get_db)):
    liquidaciones = db.query(LiquidacionCuotaCedida).all()
    return liquidaciones

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
            fecha_vencimiento_hasta=req.fecha_vencimiento_hasta
        )
        sm.settlements_resource(df_rec)
        sm.settlements_s_resource(df_s_rec)
        
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
            fecha_vencimiento_hasta=req.fecha_vencimiento_hasta
        )
        sm.settlements_resource(df_rec)
        sm.settlements_s_resource(df_s_rec)
        
        sm.execute_settlements(fecha_pago=None, cancelada=False)
        return {"status": "success", "message": "Liquidaciones procesadas exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
