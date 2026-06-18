from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from src.database import get_db
from src.logic.collections import CollectionManager
from src.api.schemas.cobranzas import CobranzaIndividual, CobranzaMasiva, ProcesoUpdate

router = APIRouter(prefix="/api/v1", tags=["Cobranzas"])

@router.post("/cobranzas/individual")
def procesar_cobranza_individual(
    datos: CobranzaIndividual,
    db: Session = Depends(get_db)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(datos.fecha_pago, datetime.min.time()) if datos.fecha_pago else datetime.today()
        fecha_corte_dt = datetime.combine(datos.fecha_corte, datetime.min.time()) if datos.fecha_corte else None
        if datos.anticipada:
            df = manager.process_early_cancellation(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt,
                vto_date=fecha_corte_dt
            )
        else:
            df = manager.process_standard_payment(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt,
                vto_date=fecha_corte_dt
            )
        return {"status": "success", "message": "Cobranza individual procesada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cobranzas/masiva")
def procesar_cobranza_masiva(
    identificador: str = Form(...),
    id_column: str = Form("A"),
    amount_column: str = Form("B"),
    fecha_pago: Optional[date] = Form(None),
    fecha_corte: Optional[date] = Form(None),
    anticipada: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(fecha_pago, datetime.min.time()) if fecha_pago else datetime.today()
        fecha_corte_dt = datetime.combine(fecha_corte, datetime.min.time()) if fecha_corte else None
        file_bytes = file.file.read()
        
        df = manager.process_massive_collection(
            identificador=identificador,
            id_column=id_column,
            amount_column=amount_column,
            payment_date=fecha_pago_dt,
            vto_date=fecha_corte_dt,
            early=anticipada,
            file_bytes=file_bytes,
            filename=file.filename
        )
        return {"status": "success", "message": "Cobranza masiva procesada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/procesos")
def get_procesos(db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso
    procesos = db.query(Proceso).order_by(desc(Proceso.fecha_ejecucion)).all()
    result = []
    for p in procesos:
        result.append({
            "ID": p.id,
            "Tipo": p.tipo.value if hasattr(p.tipo, 'value') else str(p.tipo),
            "Estado": p.estado.value if hasattr(p.estado, 'value') else str(p.estado),
            "Descripción": p.descripcion or "-",
            "Fecha Ejecución": p.fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_ejecucion else "-"
        })
    return result

@router.put("/procesos/{proceso_id}")
def update_proceso(proceso_id: int, data: ProcesoUpdate, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso, EstadoProcesoEnum
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    
    try:
        nuevo_estado = EstadoProcesoEnum(data.estado.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido.")
        
    proceso.estado = nuevo_estado
    if data.descripcion is not None:
        proceso.descripcion = data.descripcion
        
    db.commit()
    return {"status": "success", "message": "Proceso actualizado"}

@router.delete("/procesos/{proceso_id}")
def delete_proceso(proceso_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso, Cobranza
    proceso = db.query(Proceso).options(joinedload(Proceso.cobranzas).joinedload(Cobranza.liquidaciones)).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
        
    # Check if any cobranza has liquidaciones associated
    has_liquidaciones = any(len(cobranza.liquidaciones) > 0 for cobranza in proceso.cobranzas)
    if has_liquidaciones:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar el proceso porque tiene liquidaciones asociadas a sus cobranzas."
        )
        
    try:
        from src.database.models.creditos import TipoCredito
        from src.database.models.cobranzas import TipoCobranzaEnum
        
        penalty_credits = []
        for c in proceso.cobranzas:
            if c.tipo_cobranza == TipoCobranzaEnum.PENALTY:
                if c.cuota and c.cuota.credito and c.cuota.credito.tipo_credito == TipoCredito.PENALTY:
                    penalty_credits.append(c.cuota.credito)
                    
        db.delete(proceso)
        for pc in penalty_credits:
            db.delete(pc)
            
        db.commit()
        return {"status": "success", "message": "Proceso y sus cobranzas eliminados exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando el proceso: {str(e)}")

@router.get("/cobranzas")
def get_cobranzas(
    skip: int = 0,
    limit: int = 50,
    proceso_id: Optional[str] = None,
    cuil: Optional[str] = None,
    credito_id: Optional[str] = None,
    id_cobranza: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from src.database.models.cobranzas import Cobranza
    from src.database.models import Cuota, Credito
    
    query = db.query(Cobranza).options(joinedload(Cobranza.cuota).joinedload(Cuota.credito))
    
    if proceso_id:
        query = query.filter(Cobranza.proceso_id == int(proceso_id))
    if id_cobranza:
        query = query.filter(Cobranza.id == int(id_cobranza))
    if tipo:
        query = query.filter(Cobranza.tipo_cobranza == tipo)
    if cuil or credito_id:
        query = query.join(Cuota)
        if credito_id:
            query = query.filter(Cuota.credito_id == int(credito_id))
        if cuil:
            query = query.join(Credito).filter(Credito.cliente_cuil.like(f"%{cuil}%"))
            
    total = query.count()
    cobranzas = query.order_by(desc(Cobranza.fecha)).offset(skip).limit(limit).all()
    
    result = []
    for c in cobranzas:
        cuota_nro = str(c.cuota.nro_cuota) if c.cuota else "-"
        cuota_vto = c.cuota.fecha_vencimiento.strftime("%Y-%m-%d") if c.cuota and c.cuota.fecha_vencimiento else "-"
        credito_id_str = str(c.cuota.credito_id) if c.cuota else "-"
        cliente_cuil_str = c.cuota.credito.cliente_cuil if c.cuota and c.cuota.credito else "-"
        
        result.append({
            "ID": c.id,
            "Proceso ID": str(c.proceso_id) if c.proceso_id else "-",
            "Fecha Emision": c.fecha.strftime("%Y-%m-%d") if c.fecha else "-",
            "Credito ID": credito_id_str,
            "Cliente CUIL": cliente_cuil_str,
            "Cuota Nro": cuota_nro,
            "Fecha Vencimiento": cuota_vto,
            "Tipo": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, 'value') else str(c.tipo_cobranza),
            "Capital": float(c.capital),
            "Interes": float(c.interes),
            "IVA": float(c.iva),
            "Total": float(c.capital + c.interes + c.iva)
        })
    return {"items": result, "total": total}

@router.delete("/cobranzas/{cobranza_id}")
def delete_cobranza(cobranza_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    cobranza = db.query(Cobranza).filter(Cobranza.id == cobranza_id).first()
    if not cobranza:
        raise HTTPException(status_code=404, detail="Cobranza no encontrada")
        
    if len(cobranza.liquidaciones) > 0:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar la cobranza porque tiene liquidaciones asociadas."
        )
        
    cuota = cobranza.cuota
    credito = cuota.credito if cuota else None
    
    try:
        db.delete(cobranza)
        db.flush()
        
        from datetime import date
        hoy = date.today()
        if cuota:
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            
        db.commit()
        return {"status": "success", "message": "Cobranza eliminada exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando la cobranza: {str(e)}")

@router.put("/cobranzas/{cobranza_id}")
def modificar_cobranza(cobranza_id: int, datos: CobranzaIndividual, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    cobranza = db.query(Cobranza).filter(Cobranza.id == cobranza_id).first()
    if not cobranza:
        raise HTTPException(status_code=404, detail="Cobranza no encontrada")
        
    if len(cobranza.liquidaciones) > 0:
        raise HTTPException(
            status_code=400, 
            detail="No se puede modificar la cobranza porque tiene liquidaciones asociadas."
        )
        
    cuota = cobranza.cuota
    credito = cuota.credito if cuota else None
    
    try:
        db.delete(cobranza)
        db.flush()
        
        from datetime import date
        hoy = date.today()
        if cuota:
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando la cobranza original: {str(e)}")
        
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(datos.fecha_pago, datetime.min.time()) if datos.fecha_pago else datetime.today()
        if datos.anticipada:
            df = manager.process_early_cancellation(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt
            )
        else:
            df = manager.process_standard_payment(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt
            )
        return {"status": "success", "message": "Cobranza modificada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
