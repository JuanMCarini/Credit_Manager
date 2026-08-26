from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import tempfile
from pathlib import Path
from src.logic.deuda.suscripcion import nueva_serie

from src.database import get_db
from src.database.models.deuda.inversores import Inversor, CuentaComitente, TitularidadCuentaComitente
from src.database.models.deuda.series import Serie
from src.database.models.deuda.movimientos import MovimientoDeuda, TipoMovimiento
from sqlalchemy.sql import func
from src.api.schemas.inversores import (
    InversorCreate, InversorResponse,
    CuentaComitenteCreate, CuentaComitenteResponse,
    SerieCreate, SerieResponse,
    MovimientoDeudaCreate, MovimientoDeudaResponse
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
            "id_bcbb": c.id_bcbb,
            "conjunta": c.conjunta,
            "created_at": c.created_at,
            "titulares": titulares
        })
    return {"items": items, "total": total}

@router.put("/cuentas/{cuenta_id}", response_model=Dict[str, Any])
def update_cuenta_comitente(cuenta_id: int, cuenta_data: CuentaComitenteCreate, db: Session = Depends(get_db)):
    cuenta = db.query(CuentaComitente).filter(CuentaComitente.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta comitente no encontrada")
    
    try:
        data = cuenta_data.dict()
        titulares_data = data.pop("titulares", [])
        
        cuenta.id_bcbb = data["id_bcbb"]
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
        (MovimientoDeuda.id_serie == Serie.id) & (MovimientoDeuda.tipo_movimiento == TipoMovimiento.SUSCRIPCION)
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
        joinedload(MovimientoDeuda.cuenta_comitente),
        joinedload(MovimientoDeuda.serie)
    )
    total = query.count()
    movimientos = query.order_by(MovimientoDeuda.fecha.desc(), MovimientoDeuda.id.desc()).offset(skip).limit(limit).all()
    
    items = []
    for m in movimientos:
        items.append({
            "id": m.id,
            "id_cuenta_comitente": m.id_cuenta_comitente,
            "cuenta_bcbb": m.cuenta_comitente.id_bcbb if m.cuenta_comitente else None,
            "id_serie": m.id_serie,
            "serie_name": m.serie.name if m.serie else None,
            "fecha": m.fecha,
            "monto": float(m.monto),
            "tipo_movimiento": m.tipo_movimiento.value,
            "created_at": m.created_at
        })
    return {"items": items, "total": total}
