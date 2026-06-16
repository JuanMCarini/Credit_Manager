import math
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, String, asc, desc

from src.database import get_db, Provincia, Empleador, SocioComercial, TasaYComision, Relacion
from src.api.schemas.auxiliares import TabulatorRequest

router = APIRouter(prefix="/api/v1/auxiliares", tags=["Auxiliares"])

AUX_TABLES = {
    "provincias": Provincia,
    "empleadores": Empleador,
    "socios": SocioComercial,
    "tasas_y_comisiones": TasaYComision,
    "relaciones": Relacion
}

def _parse_aux_payload(payload: dict) -> dict:
    parsed = {}
    from datetime import datetime
    for k, v in payload.items():
        if isinstance(v, str):
            try:
                if len(v) == 10 and v[4] == '-' and v[7] == '-':
                    parsed[k] = datetime.strptime(v, "%Y-%m-%d").date()
                    continue
            except ValueError:
                pass
        parsed[k] = v
    return parsed

@router.post("/{tabla}/data")
def get_aux_table_data(tabla: str, request: TabulatorRequest, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    model = AUX_TABLES[tabla]
    query = db.query(model)

    if request.filter:
        for f in request.filter:
            if not hasattr(model, f.field):
                continue
            column = getattr(model, f.field)
            
            if f.type == "like":
                query = query.filter(cast(column, String).ilike(f"%{f.value}%"))
            elif f.type == "=":
                query = query.filter(column == f.value)
            elif f.type == "!=":
                query = query.filter(column != f.value)
            elif f.type == ">":
                query = query.filter(column > f.value)
            elif f.type == "<":
                query = query.filter(column < f.value)
            elif f.type == ">=":
                query = query.filter(column >= f.value)
            elif f.type == "<=":
                query = query.filter(column <= f.value)
    
    total_count = query.count()
    last_page = math.ceil(total_count / request.size) if request.size > 0 else 1

    if request.sort:
        for s in request.sort:
            if not hasattr(model, s.field):
                continue
            column = getattr(model, s.field)
            if s.dir == "asc":
                query = query.order_by(asc(column))
            elif s.dir == "desc":
                query = query.order_by(desc(column))

    query = query.offset((request.page - 1) * request.size).limit(request.size)
    records = query.all()

    data = [
        {c.name: getattr(r, c.name) for c in model.__table__.columns}
        for r in records
    ]

    return {
        "last_page": last_page,
        "data": data
    }


@router.get("/socios_originadores")
def get_socios_originadores(db: Session = Depends(get_db)):
    from src.database.models import SocioComercial, Credito
    originadores = db.query(SocioComercial).join(Credito, Credito.socio_originador_id == SocioComercial.id).distinct().all()
    return [
        {c.name: getattr(r, c.name) for c in SocioComercial.__table__.columns}
        for r in originadores
    ]

@router.get("/{tabla}")
def get_aux_table(tabla: str, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    model = AUX_TABLES[tabla]
    records = db.query(model).all()
    return [
        {c.name: getattr(r, c.name) for c in model.__table__.columns}
        for r in records
    ]

@router.post("/{tabla}")
def create_aux_record(tabla: str, payload: dict, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    payload = _parse_aux_payload(payload)
    try:
        if tabla == "socios":
            nuevo = SocioComercial.create_socio(db=db, **payload)
        else:
            model = AUX_TABLES[tabla]
            nuevo = model(**payload)
            db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return {"status": "success", "id": getattr(nuevo, "id", None)}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Los datos ingresados no son válidos (Verifique que los números y las fechas tengan el formato correcto).")
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad: Ya existe un registro con esos datos únicos.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{tabla}/{record_id}")
def update_aux_record(tabla: str, record_id: int, payload: dict, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    model = AUX_TABLES[tabla]
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    
    payload = _parse_aux_payload(payload)
    try:
        for key, value in payload.items():
            if hasattr(record, key) and key != "id":
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return {"status": "success", "id": record.id}
    except TypeError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Los datos ingresados no son válidos (Verifique que los números y las fechas tengan el formato correcto).")
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar: Datos duplicados u otro conflicto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{tabla}/{record_id}")
def delete_aux_record(tabla: str, record_id: int, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    model = AUX_TABLES[tabla]
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    
    try:
        db.delete(record)
        db.commit()
        return {"status": "success", "message": "Registro eliminado exitosamente."}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar este registro porque está siendo utilizado por otros registros en el sistema (restricción de integridad referencial)."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
