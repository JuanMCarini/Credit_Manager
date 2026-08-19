from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import uuid

from src.database.connection import get_db
from src.database.models.cheques.main import Cheque, OperadorCheque, OperacionCheque, EstadoCheque, TipoOperacionCheque
from src.database.models.finance.bancos import Movimiento
from src.api.schemas.cheques import (
    ChequeCreate, ChequeResponse, OperadorChequeCreate, OperadorChequeResponse,
    OperacionChequeCreate, OperacionChequeResponse, ChequeAsignarMovimiento
)
from src.config import COMPANY_DATA

router = APIRouter(prefix="/api/cheques", tags=["cheques"])

@router.get("/operadores", response_model=List[OperadorChequeResponse])
def listar_operadores(db: Session = Depends(get_db)):
    return db.query(OperadorCheque).all()

@router.post("/operadores", response_model=OperadorChequeResponse, status_code=status.HTTP_201_CREATED)
def crear_operador(operador: OperadorChequeCreate, db: Session = Depends(get_db)):
    db_operador = db.query(OperadorCheque).filter(OperadorCheque.cuit == operador.cuit).first()
    if db_operador:
        raise HTTPException(status_code=400, detail="El operador ya existe")
    
    nuevo_operador = OperadorCheque(**operador.model_dump())
    db.add(nuevo_operador)
    db.commit()
    db.refresh(nuevo_operador)
    return nuevo_operador

@router.put("/operadores/{cuit}", response_model=OperadorChequeResponse)
def actualizar_operador(cuit: str, operador: OperadorChequeCreate, db: Session = Depends(get_db)):
    db_operador = db.query(OperadorCheque).filter(OperadorCheque.cuit == cuit).first()
    if not db_operador:
        raise HTTPException(status_code=404, detail="El operador no existe")
    
    update_data = operador.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_operador, key, value)
        
    db.commit()
    db.refresh(db_operador)
    return db_operador

@router.delete("/operadores/{cuit}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_operador(cuit: str, db: Session = Depends(get_db)):
    db_operador = db.query(OperadorCheque).filter(OperadorCheque.cuit == cuit).first()
    if not db_operador:
        raise HTTPException(status_code=404, detail="El operador no existe")
        
    if db.query(Cheque).filter(Cheque.emisor_cuit == cuit).first() or db.query(OperacionCheque).filter(OperacionCheque.operador_cuil == cuit).first():
        raise HTTPException(status_code=400, detail="No se puede eliminar porque hay cheques u operaciones asociadas a este operador")
        
    db.delete(db_operador)
    db.commit()
    return None

@router.get("/", response_model=List[ChequeResponse])
def listar_cheques(db: Session = Depends(get_db)):
    cheques = db.query(Cheque).all()
    response_list = []
    for c in cheques:
        c_dict = ChequeResponse.model_validate(c).model_dump()
        c_dict['es_propio'] = (c.emisor_cuit == COMPANY_DATA.cuit)
        
        beneficiario_cuit = None
        if c.operaciones:
            ultima_op = max(c.operaciones, key=lambda x: (x.fecha_operacion, x.id))
            beneficiario_cuit = ultima_op.operador_cuil
        else:
            beneficiario_cuit = c.emisor_cuit
        c_dict['is_beneficiario_empresa'] = (beneficiario_cuit == COMPANY_DATA.cuit)
        
        response_list.append(c_dict)
    
    return response_list

@router.post("/", response_model=ChequeResponse, status_code=status.HTTP_201_CREATED)
def crear_cheque(cheque_in: ChequeCreate, db: Session = Depends(get_db)):
    db_emisor = db.query(OperadorCheque).filter(OperadorCheque.cuit == cheque_in.emisor_cuit).first()
    if not db_emisor:
        raise HTTPException(status_code=400, detail="El emisor no existe")

    nuevo_cheque = Cheque(**cheque_in.model_dump())
    db.add(nuevo_cheque)
    db.commit()
    db.refresh(nuevo_cheque)
    
    c_dict = ChequeResponse.model_validate(nuevo_cheque).model_dump()
    c_dict['es_propio'] = (nuevo_cheque.emisor_cuit == COMPANY_DATA.cuit)
    c_dict['is_beneficiario_empresa'] = (nuevo_cheque.emisor_cuit == COMPANY_DATA.cuit) # Al crear, el beneficiario es el emisor
    return c_dict

@router.put("/{cheque_id}", response_model=ChequeResponse)
def actualizar_cheque(cheque_id: int, cheque_in: ChequeCreate, db: Session = Depends(get_db)):
    db_cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not db_cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
        
    if db_cheque.estado != EstadoCheque.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden modificar cheques en estado PENDIENTE")

    db_emisor = db.query(OperadorCheque).filter(OperadorCheque.cuit == cheque_in.emisor_cuit).first()
    if not db_emisor:
        raise HTTPException(status_code=400, detail="El emisor no existe")

    update_data = cheque_in.model_dump()
    for key, value in update_data.items():
        setattr(db_cheque, key, value)
        
    db.commit()
    db.refresh(db_cheque)
    c_dict = ChequeResponse.model_validate(db_cheque).model_dump()
    c_dict['es_propio'] = (db_cheque.emisor_cuit == COMPANY_DATA.cuit)
    
    beneficiario_cuit = None
    if db_cheque.operaciones:
        ultima_op = max(db_cheque.operaciones, key=lambda x: (x.fecha_operacion, x.id))
        beneficiario_cuit = ultima_op.operador_cuil
    else:
        beneficiario_cuit = db_cheque.emisor_cuit
    c_dict['is_beneficiario_empresa'] = (beneficiario_cuit == COMPANY_DATA.cuit)
    
    return c_dict

@router.delete("/{cheque_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cheque(cheque_id: int, db: Session = Depends(get_db)):
    db_cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not db_cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
        
    if db_cheque.estado != EstadoCheque.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar cheques en estado PENDIENTE")
        
    # Check if there are related operations
    if db.query(OperacionCheque).filter(OperacionCheque.cheque_id == cheque_id).first():
        raise HTTPException(status_code=400, detail="No se puede eliminar porque el cheque tiene operaciones registradas")
        
    db.delete(db_cheque)
    db.commit()
    return None

@router.post("/{cheque_id}/operaciones", response_model=OperacionChequeResponse, status_code=status.HTTP_201_CREATED)
def operar_cheque(cheque_id: int, operacion_in: OperacionChequeCreate, db: Session = Depends(get_db)):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")

    is_own = (cheque.emisor_cuit == COMPANY_DATA.cuit)
    
    if is_own:
        if operacion_in.tipo_operacion != TipoOperacionCheque.VENTA:
            raise HTTPException(status_code=400, detail="Los cheques propios solo pueden ser VENDIDOS")
        if cheque.estado != EstadoCheque.PENDIENTE:
            raise HTTPException(status_code=400, detail="El cheque propio ya no está PENDIENTE")
    else:
        if operacion_in.tipo_operacion == TipoOperacionCheque.COMPRA:
            if cheque.estado != EstadoCheque.PENDIENTE:
                raise HTTPException(status_code=400, detail="Solo se puede COMPRAR un cheque de terceros en estado PENDIENTE")
        elif operacion_in.tipo_operacion == TipoOperacionCheque.VENTA:
            if cheque.estado != EstadoCheque.COMPRADO:
                raise HTTPException(status_code=400, detail="Solo se puede VENDER un cheque de terceros si previamente fue COMPRADO")
        else:
            raise HTTPException(status_code=400, detail="Operación no permitida")
        
    nueva_operacion = OperacionCheque(**operacion_in.model_dump(), cheque_id=cheque_id)
    db.add(nueva_operacion)
    
    if operacion_in.tipo_operacion == TipoOperacionCheque.COMPRA:
        cheque.estado = EstadoCheque.COMPRADO
    elif operacion_in.tipo_operacion == TipoOperacionCheque.VENTA:
        cheque.estado = EstadoCheque.VENDIDO
        
    db.commit()
    db.refresh(nueva_operacion)
    return nueva_operacion

@router.get("/{cheque_id}/operaciones", response_model=List[OperacionChequeResponse])
def listar_operaciones(cheque_id: int, db: Session = Depends(get_db)):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
    return cheque.operaciones

@router.put("/operaciones/{operacion_id}", response_model=OperacionChequeResponse)
def editar_operacion(operacion_id: int, operacion_in: OperacionChequeCreate, db: Session = Depends(get_db)):
    db_op = db.query(OperacionCheque).filter(OperacionCheque.id == operacion_id).first()
    if not db_op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
        
    update_data = operacion_in.model_dump()
    for key, value in update_data.items():
        setattr(db_op, key, value)
        
    db.commit()
    db.refresh(db_op)
    return db_op

@router.delete("/operaciones/{operacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_operacion(operacion_id: int, db: Session = Depends(get_db)):
    db_op = db.query(OperacionCheque).filter(OperacionCheque.id == operacion_id).first()
    if not db_op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
        
    cheque = db_op.cheque
    db.delete(db_op)
    db.commit()
    
    # Refresh to see remaining operations
    db.refresh(cheque)
    if not cheque.operaciones:
        cheque.estado = EstadoCheque.PENDIENTE
    else:
        # Revert to the state of the last operation
        last_op = max(cheque.operaciones, key=lambda x: (x.fecha_operacion, x.id))
        if last_op.tipo_operacion == TipoOperacionCheque.COMPRA:
            cheque.estado = EstadoCheque.COMPRADO
        elif last_op.tipo_operacion == TipoOperacionCheque.VENTA:
            cheque.estado = EstadoCheque.VENDIDO
            
    db.commit()
    return None


@router.post("/{cheque_id}/imagen", status_code=status.HTTP_200_OK)
def upload_cheque_imagen(
    cheque_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    db_cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not db_cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
        
    upload_dir = "data/uploads/cheques"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
        raise HTTPException(status_code=400, detail="Formato no soportado. Solo JPG, PNG o PDF.")
        
    filename = f"cheque_{cheque_id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    # Store relative path so the frontend can query it directly via /static
    db_path = f"cheques/{filename}"
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_cheque.imagen_path = db_path
    db.commit()
    
    return {"message": "Imagen subida correctamente", "imagen_path": db_path}

@router.post("/{cheque_id}/asignar_movimiento", response_model=ChequeResponse, status_code=status.HTTP_200_OK)
def asignar_movimiento(cheque_id: int, payload: ChequeAsignarMovimiento, db: Session = Depends(get_db)):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
        
    if cheque.movimiento_id is not None:
        raise HTTPException(status_code=400, detail="El cheque ya tiene un movimiento bancario asignado")
        
    mov = db.query(Movimiento).filter(Movimiento.id == payload.movimiento_id).first()
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento bancario no encontrado")
        
    is_propio = (cheque.emisor_cuit == COMPANY_DATA.cuit)
    
    # Determinar si el beneficiario actual es la empresa
    # if cheque.operaciones it uses the last one, otherwise emisor
    beneficiario_actual_cuit = None
    if cheque.operaciones:
        ultima_op = max(cheque.operaciones, key=lambda x: (x.fecha_operacion, x.id))
        beneficiario_actual_cuit = ultima_op.operador_cuil
    else:
        beneficiario_actual_cuit = cheque.emisor_cuit
        
    is_beneficiario_empresa = (beneficiario_actual_cuit == COMPANY_DATA.cuit)
    
    if is_propio:
        cheque.estado = EstadoCheque.DEBITADO
    elif is_beneficiario_empresa:
        cheque.estado = EstadoCheque.ACREDITADO
    else:
        raise HTTPException(status_code=400, detail="No se puede asignar movimiento: el cheque no fue emitido por la empresa ni está en cartera")
        
    cheque.movimiento_id = mov.id
    db.commit()
    db.refresh(cheque)
    
    c_dict = ChequeResponse.model_validate(cheque).model_dump()
    c_dict['es_propio'] = is_propio
    c_dict['is_beneficiario_empresa'] = is_beneficiario_empresa
    return c_dict

@router.post("/{cheque_id}/desasignar_movimiento", response_model=ChequeResponse, status_code=status.HTTP_200_OK)
def desasignar_movimiento(cheque_id: int, db: Session = Depends(get_db)):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
        
    if cheque.movimiento_id is None:
        raise HTTPException(status_code=400, detail="El cheque no tiene un movimiento asignado")
        
    cheque.movimiento_id = None
    
    # Revertir estado lógico
    if not cheque.operaciones:
        cheque.estado = EstadoCheque.PENDIENTE
    else:
        last_op = max(cheque.operaciones, key=lambda x: (x.fecha_operacion, x.id))
        if last_op.tipo_operacion == TipoOperacionCheque.COMPRA:
            cheque.estado = EstadoCheque.COMPRADO
        elif last_op.tipo_operacion == TipoOperacionCheque.VENTA:
            cheque.estado = EstadoCheque.VENDIDO
            
    db.commit()
    db.refresh(cheque)
    
    is_propio = (cheque.emisor_cuit == COMPANY_DATA.cuit)
    beneficiario_actual_cuit = None
    if cheque.operaciones:
        ultima_op = max(cheque.operaciones, key=lambda x: (x.fecha_operacion, x.id))
        beneficiario_actual_cuit = ultima_op.operador_cuil
    else:
        beneficiario_actual_cuit = cheque.emisor_cuit
    is_beneficiario_empresa = (beneficiario_actual_cuit == COMPANY_DATA.cuit)
    
    c_dict = ChequeResponse.model_validate(cheque).model_dump()
    c_dict['es_propio'] = is_propio
    c_dict['is_beneficiario_empresa'] = is_beneficiario_empresa
    return c_dict
