from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import tempfile
from pathlib import Path
from src.logic.deuda.suscripcion import nueva_serie
from src.logic.deuda.vencimiento import renovación
from src.logic.deuda.series import resumen as buscar_resumen_serie

from src.database import get_db
from src.database.models.deuda.inversores import Inversor, CuentaComitente, TitularidadCuentaComitente
from src.database.models.deuda.series import Serie
from src.database.models.deuda.movimientos import MovimientoDeuda, TipoMovimiento, TitularidadMovimientoDeuda
from sqlalchemy.sql import func
from src.api.schemas.inversores import (
    InversorCreate, InversorResponse,
    CuentaComitenteCreate, CuentaComitenteResponse,
    SerieCreate, SerieUpdate, SerieResponse,
    MovimientoDeudaCreate, MovimientoDeudaUpdate, MovimientoDeudaResponse
)

router = APIRouter(prefix="/api/v1/inversores", tags=["Inversores"])

# -----------------
# INVERSORES
# -----------------
@router.post("", response_model=Dict[str, Any])
def create_inversor(
    inversor_data: InversorCreate,
    db: Session = Depends(get_db)
):
    try:
        nuevo_inversor = Inversor(**inversor_data.dict())
        db.add(nuevo_inversor)
        db.commit()
        db.refresh(nuevo_inversor)
        return {"status": "success", "message": "Inversor creado exitosamente", "id": nuevo_inversor.id}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. El CUIT o Razón Social ya están registrados.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=Dict[str, Any])
def get_inversores(
    skip: int = 0,
    limit: int = 1000,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Inversor)
    if search:
        query = query.filter(
            or_(
                Inversor.cuit.like(f"%{search}%"),
                Inversor.razon_social.ilike(f"%{search}%")
            )
        )
    total = query.count()
    inversores = query.order_by(Inversor.id.desc()).offset(skip).limit(limit).all()
    
    # Map to schema manually or use schema dumping
    items = []
    for inv in inversores:
        items.append({
            "id": inv.id,
            "cuit": inv.cuit,
            "razon_social": inv.razon_social,
            "domicilio_legal": inv.domicilio_legal,
            "mail": inv.mail,
            "telefono": inv.telefono,
            "cbu": inv.cbu,
            "nro_cuenta_bancaria": inv.nro_cuenta_bancaria,
            "nombre_banco": inv.nombre_banco,
            "activo": inv.activo,
            "created_at": inv.created_at
        })
    return {"items": items, "total": total}

@router.delete("/{inversor_id}")
def delete_inversor(inversor_id: int, db: Session = Depends(get_db)):
    inversor = db.query(Inversor).filter(Inversor.id == inversor_id).first()
    if not inversor:
        raise HTTPException(status_code=404, detail="Inversor no encontrado")
    try:
        db.delete(inversor)
        db.commit()
        return {"status": "success", "message": "Inversor eliminado"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se puede eliminar el inversor porque está asociado a cuentas comitentes u otras entidades.")

@router.put("/{inversor_id}", response_model=Dict[str, Any])
def update_inversor(inversor_id: int, inversor_data: InversorCreate, db: Session = Depends(get_db)):
    inversor = db.query(Inversor).filter(Inversor.id == inversor_id).first()
    if not inversor:
        raise HTTPException(status_code=404, detail="Inversor no encontrado")
    
    try:
        update_data = inversor_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(inversor, key, value)
            
        db.commit()
        db.refresh(inversor)
        return {"status": "success", "message": "Inversor actualizado", "id": inversor.id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. El CUIT o Razón Social ya están registrados.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# -----------------
# CUENTAS COMITENTES
# -----------------
@router.post("/cuentas", response_model=Dict[str, Any])
def create_cuenta_comitente(
    cuenta_data: CuentaComitenteCreate,
    db: Session = Depends(get_db)
):
    try:
        data = cuenta_data.dict()
        titulares_data = data.pop("titulares", [])
        
        nueva_cuenta = CuentaComitente(**data)
        db.add(nueva_cuenta)
        db.flush() # get id
        
        for t in titulares_data:
            titularidad = TitularidadCuentaComitente(
                id_cuenta_comitente=nueva_cuenta.id,
                id_inversor=t["id_inversor"],
                orden=t["orden"],
                activo=t["activo"]
            )
            db.add(titularidad)
            
        db.commit()
        db.refresh(nueva_cuenta)
        return {"status": "success", "message": "Cuenta comitente creada exitosamente", "id": nueva_cuenta.id}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. Puede que el ID BCBB ya exista.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cuentas", response_model=Dict[str, Any])
def get_cuentas_comitentes(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    query = db.query(CuentaComitente).options(
        joinedload(CuentaComitente.titulares_assoc).joinedload(TitularidadCuentaComitente.inversor)
    )
    total = query.count()
    cuentas = query.order_by(CuentaComitente.id.desc()).offset(skip).limit(limit).all()
    
    items = []
    for c in cuentas:
        titulares = []
        for t in c.titulares_assoc:
            titulares.append({
                "orden": t.orden,
                "inversor_razon_social": t.inversor.razon_social,
                "inversor_cuit": t.inversor.cuit,
                "inversor_id": t.inversor.id
            })
        items.append({
            "id": c.id,
            "id_externo": c.id_externo,
            "conjunta": c.conjunta,
            "created_at": c.created_at,
            "titulares": titulares
        })
    return {"items": items, "total": total}

import pandas as pd
from src.logic.deuda.ctas_ctes import buscar as buscar_ctas_ctes

@router.get("/cuentas/{cuenta_id}/estado", response_model=Dict[str, Any])
def get_estado_cuenta(cuenta_id: int):
    try:
        df_inv, df_mov = buscar_ctas_ctes(cuenta_id)
        
        # Format datetimes
        for col in df_mov.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
            df_mov[col] = df_mov[col].dt.strftime('%Y-%m-%d')
            
        for col in df_inv.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
            df_inv[col] = df_inv[col].dt.strftime('%Y-%m-%d')
            
        # Replace NaNs with None for JSON serialization
        df_inv = df_inv.replace({pd.NA: None, float('nan'): None})
        df_mov = df_mov.replace({pd.NA: None, float('nan'): None})
        
        inv_records = df_inv.reset_index().to_dict(orient="records")
        mov_records = df_mov.to_dict(orient="records")
        
        return {
            "status": "success",
            "inversores": inv_records,
            "movimientos": mov_records
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cuentas/{cuenta_id}", response_model=Dict[str, Any])
def update_cuenta_comitente(cuenta_id: int, cuenta_data: CuentaComitenteCreate, db: Session = Depends(get_db)):
    cuenta = db.query(CuentaComitente).filter(CuentaComitente.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta comitente no encontrada")
    
    try:
        data = cuenta_data.dict()
        titulares_data = data.pop("titulares", [])
        
        cuenta.id_externo = data["id_externo"]
        cuenta.conjunta = data["conjunta"]
        
        # Eliminar titulares viejos
        db.query(TitularidadCuentaComitente).filter(TitularidadCuentaComitente.id_cuenta_comitente == cuenta_id).delete()
        
        # Agregar nuevos titulares
        for t in titulares_data:
            titularidad = TitularidadCuentaComitente(
                id_cuenta_comitente=cuenta_id,
                id_inversor=t["id_inversor"],
                orden=t["orden"],
                activo=t["activo"]
            )
            db.add(titularidad)
            
        db.commit()
        return {"status": "success", "message": "Cuenta comitente actualizada", "id": cuenta.id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. Puede que el ID BCBB ya exista.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cuentas/{cuenta_id}")
def delete_cuenta_comitente(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = db.query(CuentaComitente).filter(CuentaComitente.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta comitente no encontrada")
    try:
        db.query(TitularidadCuentaComitente).filter(TitularidadCuentaComitente.id_cuenta_comitente == cuenta_id).delete()
        db.delete(cuenta)
        db.commit()
        return {"status": "success", "message": "Cuenta comitente eliminada"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se puede eliminar la cuenta porque tiene movimientos asociados.")

# -----------------
# SERIES
# -----------------
@router.post("/series", response_model=Dict[str, Any])
def create_serie(
    serie_data: SerieCreate,
    db: Session = Depends(get_db)
):
    try:
        nueva_serie = Serie(**serie_data.dict())
        db.add(nueva_serie)
        db.commit()
        db.refresh(nueva_serie)
        return {"status": "success", "message": "Serie creada exitosamente", "id": nueva_serie.id}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. El nombre de la serie ya existe.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/series/upload", response_model=Dict[str, Any])
def upload_serie(
    name: str = Form(...),
    fecha_suscripcion: str = Form(...),
    tna: float = Form(...),
    plazo: int = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = Path(tmp.name)
            
        # Call the business logic
        nueva_serie(
            nombre=name, 
            fecha=fecha_suscripcion, 
            tna=tna, 
            plazo=plazo, 
            path=tmp_path
        )
        
        # Cleanup
        tmp_path.unlink(missing_ok=True)
        
        return {
            "status": "success", 
            "message": "Serie y suscripciones procesadas exitosamente",
            "totals": {}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/series/renovacion", response_model=Dict[str, Any])
def renovacion_serie(
    serie_vieja: str = Form(...),
    serie_nueva: str = Form(...),
    fecha_suscripcion: str = Form(...),
    tna: float = Form(...),
    plazo: int = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = Path(tmp.name)
            
        # Call the business logic
        df_ei = renovación(
            serie_vieja=serie_vieja,
            serie_nueva=serie_nueva, 
            fecha=fecha_suscripcion, 
            tna=tna, 
            plazo=plazo, 
            path=tmp_path
        )
        
        # Cleanup
        tmp_path.unlink(missing_ok=True)
        
        # Convert df_ei to json format
        records = df_ei.fillna("").to_dict(orient="records")
        
        return {
            "status": "success", 
            "message": "Renovación procesada exitosamente",
            "df_ei": records
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/series", response_model=Dict[str, Any])
def get_series(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    query = db.query(
        Serie,
        func.coalesce(func.sum(MovimientoDeuda.monto), 0).label("capital")
    ).outerjoin(
        MovimientoDeuda,
        (MovimientoDeuda.id_serie == Serie.id) & (MovimientoDeuda.tipo_movimiento.in_([TipoMovimiento.SUSCRIPCION, TipoMovimiento.RENOVACION_SUSCRIPCION]))
    ).group_by(Serie.id).order_by(Serie.id.desc())
    
    total = db.query(Serie).count()
    results = query.offset(skip).limit(limit).all()
    
    items = []
    for s, capital in results:
        items.append({
            "id": s.id,
            "name": s.name,
            "fecha_suscripcion": s.fecha_suscripcion,
            "tna": float(s.tna),
            "plazo": s.plazo,
            "fecha_vencimiento": s.fecha_vencimiento,
            "created_at": s.created_at,
            "capital": float(capital)
        })
    return {"items": items, "total": total}

@router.get("/series/{serie_id}/resumen", response_model=Dict[str, Any])
def get_resumen_serie(serie_id: int):
    try:
        df = buscar_resumen_serie(serie_id)
        if df.empty:
            return {"status": "success", "data": []}
            
        # Format datetimes
        for col in df.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
            df[col] = df[col].dt.strftime('%Y-%m-%d')
            
        # Replace NaNs with None for JSON serialization
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient="records")
        return {"status": "success", "data": records}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/series/{serie_id}", response_model=Dict[str, Any])
def update_serie(
    serie_id: int,
    serie_data: SerieUpdate,
    db: Session = Depends(get_db)
):
    try:
        serie = db.query(Serie).filter(Serie.id == serie_id).first()
        if not serie:
            raise HTTPException(status_code=404, detail="Serie no encontrada")

        update_data = serie_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(serie, key, value)

        db.commit()
        db.refresh(serie)
        return {"status": "success", "message": "Serie actualizada exitosamente"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. El nombre de la serie ya existe.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/series/{serie_id}", response_model=Dict[str, Any])
def delete_serie(
    serie_id: int,
    db: Session = Depends(get_db)
):
    try:
        serie = db.query(Serie).filter(Serie.id == serie_id).first()
        if not serie:
            raise HTTPException(status_code=404, detail="Serie no encontrada")

        db.delete(serie)
        db.commit()
        return {"status": "success", "message": "Serie y sus movimientos asociados eliminados exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
# -----------------
# MOVIMIENTOS
# -----------------
@router.post("/movimientos", response_model=Dict[str, Any])
def create_movimiento(
    movimiento_data: MovimientoDeudaCreate,
    db: Session = Depends(get_db)
):
    try:
        nuevo_movimiento = MovimientoDeuda(**movimiento_data.dict())
        db.add(nuevo_movimiento)
        db.commit()
        db.refresh(nuevo_movimiento)
        return {"status": "success", "message": "Movimiento registrado exitosamente", "id": nuevo_movimiento.id}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad. Verifique la cuenta comitente y la serie.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/movimientos", response_model=Dict[str, Any])
def get_movimientos(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    query = db.query(MovimientoDeuda).options(
        joinedload(MovimientoDeuda.cuenta_comitente).joinedload(CuentaComitente.titulares_assoc).joinedload(TitularidadCuentaComitente.inversor),
        joinedload(MovimientoDeuda.titulares_assoc).joinedload(TitularidadMovimientoDeuda.inversor),
        joinedload(MovimientoDeuda.serie)
    )
    total = query.count()
    movimientos = query.order_by(MovimientoDeuda.fecha.desc(), MovimientoDeuda.id.desc()).offset(skip).limit(limit).all()
    
    items = []
    for m in movimientos:
        titulares = []
        if m.titulares_assoc:
            # Usar titulares específicos del movimiento
            for idx, t in enumerate(m.titulares_assoc):
                titulares.append({
                    "orden": idx + 1,
                    "inversor_razon_social": t.inversor.razon_social,
                    "inversor_cuit": t.inversor.cuit,
                    "inversor_id": t.inversor.id
                })
        elif m.cuenta_comitente and m.cuenta_comitente.titulares_assoc:
            # Fallback a los titulares de la cuenta comitente
            for t in m.cuenta_comitente.titulares_assoc:
                titulares.append({
                    "orden": t.orden,
                    "inversor_razon_social": t.inversor.razon_social,
                    "inversor_cuit": t.inversor.cuit,
                    "inversor_id": t.inversor.id
                })
        items.append({
            "id": m.id,
            "id_cuenta_comitente": m.id_cuenta_comitente,
            "cuenta_externo": m.cuenta_comitente.id_externo if m.cuenta_comitente else None,
            "titulares": titulares,
            "id_serie": m.id_serie,
            "serie_name": m.serie.name if m.serie else None,
            "fecha": m.fecha,
            "monto": float(m.monto),
            "tipo_movimiento": m.tipo_movimiento.value,
            "observaciones": m.observaciones,
            "created_at": m.created_at
        })
    return {"items": items, "total": total}

@router.put("/movimientos/{movimiento_id}", response_model=Dict[str, Any])
def update_movimiento(
    movimiento_id: int,
    movimiento_data: MovimientoDeudaUpdate,
    db: Session = Depends(get_db)
):
    movimiento = db.query(MovimientoDeuda).filter(MovimientoDeuda.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    update_data = movimiento_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(movimiento, key, value)
        
    try:
        db.commit()
        db.refresh(movimiento)
        return {"status": "success", "message": "Movimiento actualizado", "id": movimiento.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/movimientos/{movimiento_id}", response_model=Dict[str, Any])
def delete_movimiento(
    movimiento_id: int,
    db: Session = Depends(get_db)
):
    movimiento = db.query(MovimientoDeuda).filter(MovimientoDeuda.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    try:
        db.delete(movimiento)
        db.commit()
        return {"status": "success", "message": "Movimiento eliminado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
