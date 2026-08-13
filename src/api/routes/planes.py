from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_
from typing import List

from src.database.connection import get_db
from src.database.models.finance.planes import Plan
from src.database.models.finance.comprobantes import Comprobante, TipoComprobante, EstadoComprobante
from dateutil.relativedelta import relativedelta
import datetime
from src.api.schemas.planes import PlanCreate, PlanResponse

router = APIRouter(prefix="/api/finanzas/planes", tags=["Planes de Pago"])

@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(plan_in: PlanCreate, db: Session = Depends(get_db)):
    # Check if id_origen already exists
    existing_plan = db.execute(select(Plan).where(Plan.id_origen == plan_in.id_origen)).scalar_one_or_none()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Ya existe un plan con ese ID Origen")
    
    db_plan = Plan(**plan_in.model_dump())
    db.add(db_plan)
    
    try:
        db.commit()
        db.refresh(db_plan)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
        
    return db_plan

@router.get("", response_model=List[PlanResponse])
def get_planes(db: Session = Depends(get_db)):
    planes = db.execute(select(Plan).options(selectinload(Plan.cuotas))).scalars().all()
    return planes

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.execute(select(Plan).where(Plan.id == plan_id)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
        
    for comp in plan.cuotas:
        if comp.estado != EstadoComprobante.PENDIENTE or comp.importe_cancelado > 0:
            raise HTTPException(status_code=400, detail="No se puede eliminar el plan porque tiene comprobantes con pagos registrados.")
            
    db.delete(plan)
    db.commit()
    return None

@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: int, plan_in: PlanCreate, db: Session = Depends(get_db)):
    plan = db.execute(select(Plan).where(Plan.id == plan_id)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
        
    # Check if id_origen changed and exists
    if plan.id_origen != plan_in.id_origen:
        existing_plan = db.execute(select(Plan).where(Plan.id_origen == plan_in.id_origen)).scalar_one_or_none()
        if existing_plan:
            raise HTTPException(status_code=400, detail="Ya existe un plan con ese ID Origen")

    for comp in plan.cuotas:
        if comp.estado != EstadoComprobante.PENDIENTE or comp.importe_cancelado > 0:
            raise HTTPException(status_code=400, detail="No se puede modificar el plan porque tiene comprobantes con pagos registrados.")

    # Update plan fields
    for key, value in plan_in.model_dump().items():
        setattr(plan, key, value)
        
    # Remove existing cuotas explicitly
    for comp in list(plan.cuotas):
        db.delete(comp)
        
    # Generate new cuotas
    comprobantes_data = []
    
    if plan.anticipo and plan.anticipo > 0:
        comprobantes_data.append({
            "proveedor_id": plan.proveedor_id,
            "concepto_id": plan.concepto_id,
            "plan_pago_id": plan.id,
            "tipo_comprobante": TipoComprobante.CUOTA.name, 
            "punto_venta": plan.proveedor_id,
            "numero_comprobante": plan.id*1000,
            "fecha_contable": plan.fecha,
            "fecha_emision": plan.fecha,
            "fecha_vencimiento": plan.vencimiento_anticipo,
            "importe_total": plan.anticipo,
            "estado": "pendiente",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        })
        
    for i in range(1, plan.plazo+1):
        comprobantes_data.append({
            "proveedor_id": plan.proveedor_id,
            "concepto_id": plan.concepto_id,
            "plan_pago_id": plan.id,
            "tipo_comprobante": TipoComprobante.CUOTA.name,
            "punto_venta": plan.proveedor_id,
            "numero_comprobante": plan.id*1000+i,
            "fecha_contable": plan.fecha,
            "fecha_emision": plan.fecha,
            "fecha_vencimiento": plan.primer_vencimiento + relativedelta(months=i),
            "importe_total": plan.valor_cuota,
            "estado": "pendiente",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        })
        
    db.commit() # commit plan updates and deletions first
    
    # Insert new cuotas
    if comprobantes_data:
        db.execute(Comprobante.__table__.insert(), comprobantes_data)
        db.commit()
        
    db.refresh(plan)
    return plan
