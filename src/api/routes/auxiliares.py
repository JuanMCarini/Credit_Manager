import math
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, String, asc, desc

from src.database import get_db, Provincia, Empleador, SocioComercial, TasaYComision, Relacion, Comercializador
from src.api.schemas.auxiliares import TabulatorRequest

router = APIRouter(prefix="/api/v1/auxiliares", tags=["Auxiliares"])

AUX_TABLES = {
    "provincias": Provincia,
    "empleadores": Empleador,
    "socios": SocioComercial,
    "tasas_y_comisiones": TasaYComision,
    "relaciones": Relacion,
    "comercializadores": Comercializador
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

    data = []
    for r in records:
        row_dict = {c.name: getattr(r, c.name) for c in model.__table__.columns}
        if tabla == "socios":
            from src.database.models.socios import AnticiposSinAplicar
            from sqlalchemy import func
            saldo = db.query(func.sum(AnticiposSinAplicar.monto)).filter(AnticiposSinAplicar.socio_id == r.id).scalar() or 0.0
            row_dict["anticipo_vigente"] = float(saldo)
        data.append(row_dict)

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

from pydantic import BaseModel
from datetime import date

class AnticipoPayload(BaseModel):
    monto: float
    fecha: date

@router.post("/socios/{socio_id}/anticipos")
def add_socio_anticipo(socio_id: int, payload: AnticipoPayload, db: Session = Depends(get_db)):
    from src.database.models.socios import AnticiposSinAplicar, SocioComercial
    socio = db.query(SocioComercial).filter(SocioComercial.id == socio_id).first()
    if not socio:
        raise HTTPException(status_code=404, detail="Socio comercial no encontrado.")
    
    nuevo_anticipo = AnticiposSinAplicar(
        socio_id=socio_id,
        monto=payload.monto,
        fecha=payload.fecha
    )
    db.add(nuevo_anticipo)
    db.commit()
    
    return {"status": "success", "message": "Anticipo registrado exitosamente."}

@router.get("/{tabla}")
def get_aux_table(tabla: str, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    model = AUX_TABLES[tabla]
    records = db.query(model).all()
    data = []
    for r in records:
        row_dict = {c.name: getattr(r, c.name) for c in model.__table__.columns}
        if tabla == "socios":
            from src.database.models.socios import AnticiposSinAplicar
            from sqlalchemy import func
            saldo = db.query(func.sum(AnticiposSinAplicar.monto)).filter(AnticiposSinAplicar.socio_id == r.id).scalar() or 0.0
            row_dict["anticipo_vigente"] = float(saldo)
        data.append(row_dict)
    return data

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

    if tabla == "tasas_y_comisiones":
        from src.database.models import Credito
        if db.query(Credito).filter(Credito.comision_id == record_id).first():
            # Check if any structural field is being changed
            structural_changes = False
            for key, value in payload.items():
                if key not in ("id", "estado") and hasattr(record, key):
                    current_value = getattr(record, key)
                    # Convert dates and decimals for comparison if needed, or simply compare string representation
                    # Float comparison requires care, so we check string representation or float equivalence
                    if str(current_value) != str(value) and not (isinstance(current_value, float) and float(current_value) == float(value)):
                        # Some decimals from DB might be Decimals, while payload has floats. We convert both to float if possible.
                        try:
                            if float(current_value) != float(value):
                                structural_changes = True
                                break
                        except (TypeError, ValueError):
                            structural_changes = True
                            break
            
            if structural_changes:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden editar las condiciones de esta Tasa y Comisión porque existen créditos vinculados. Solo está permitido cambiar su Estado a INACTIVA."
                )
    try:
        for key, value in payload.items():
            if hasattr(record, key) and key != "id":
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        
        if tabla == "socios":
            from src.config import COMPANY_DATA, update_company_env
            if str(record.cuit) == str(COMPANY_DATA.cuit):
                update_company_env(record)

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
    
    if tabla == "tasas_y_comisiones":
        from src.database.models import Credito
        if db.query(Credito).filter(Credito.comision_id == record_id).first():
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar este registro de Tasas y Comisiones porque existen créditos asociados a él."
            )

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
