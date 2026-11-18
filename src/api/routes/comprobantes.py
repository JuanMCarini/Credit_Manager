from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os
import shutil
import uuid

from src.database import get_db
from src.database.models.finance.comprobantes import Proveedor, Comprobante, CancelacionComprobante, TipoComprobante, EstadoComprobante
from src.api.schemas.comprobantes import (
    ProveedorCreate, ProveedorUpdate, ProveedorResponse,
    ComprobanteCreate, ComprobanteUpdate, ComprobanteResponse,
    CancelacionCreate, CancelacionResponse
)

router = APIRouter(
    prefix="/api/finanzas",
    tags=["Comprobantes"]
)

# -------------------------------------------------------------------
# Proveedores
# -------------------------------------------------------------------
@router.get("/proveedores", response_model=List[ProveedorResponse])
def get_proveedores(db: Session = Depends(get_db)):
    return db.query(Proveedor).options(joinedload(Proveedor.concepto)).all()

@router.post("/proveedores", response_model=ProveedorResponse)
def create_proveedor(proveedor: ProveedorCreate, db: Session = Depends(get_db)):
    db_proveedor = Proveedor(**proveedor.model_dump())
    db.add(db_proveedor)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al crear proveedor (¿CUIT duplicado?)")
    db.refresh(db_proveedor)
    db_proveedor = db.query(Proveedor).options(joinedload(Proveedor.concepto)).filter(Proveedor.id == db_proveedor.id).first()
    return db_proveedor

@router.put("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def update_proveedor(proveedor_id: int, proveedor: ProveedorUpdate, db: Session = Depends(get_db)):
    db_proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not db_proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    for key, value in proveedor.model_dump(exclude_unset=True).items():
        setattr(db_proveedor, key, value)
    
    db.commit()
    db.refresh(db_proveedor)
    db_proveedor = db.query(Proveedor).options(joinedload(Proveedor.concepto)).filter(Proveedor.id == db_proveedor.id).first()
    return db_proveedor

@router.delete("/proveedores/{proveedor_id}")
def delete_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    db_proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not db_proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # Check for linked comprobantes
    if db.query(Comprobante).filter(Comprobante.proveedor_id == proveedor_id).count() > 0:
        raise HTTPException(status_code=400, detail="No se puede eliminar porque tiene comprobantes asociados")
        
    db.delete(db_proveedor)
    db.commit()
    return {"message": "Proveedor eliminado correctamente"}

# -------------------------------------------------------------------
# Comprobantes
# -------------------------------------------------------------------
@router.get("/comprobantes", response_model=List[ComprobanteResponse])
def get_comprobantes(db: Session = Depends(get_db)):
    comprobantes = db.query(Comprobante).options(joinedload(Comprobante.proveedor), joinedload(Comprobante.concepto)).order_by(Comprobante.fecha_contable.desc()).all()
    changed = False
    for c in comprobantes:
        if c.importe_total and c.importe_cancelado is not None:
            if c.importe_cancelado >= c.importe_total > 0 and c.estado != EstadoComprobante.PAGADO:
                c.estado = EstadoComprobante.PAGADO
                changed = True
            elif c.importe_cancelado < c.importe_total and c.importe_cancelado > 0 and c.estado != EstadoComprobante.PARCIAL:
                c.estado = EstadoComprobante.PARCIAL
                changed = True
            elif c.importe_cancelado == 0 and c.estado != EstadoComprobante.PENDIENTE:
                c.estado = EstadoComprobante.PENDIENTE
                changed = True
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
    return comprobantes

from decimal import Decimal


def _autocalcular_iva_y_total(db_comp: Comprobante, importe_total_recibido: Optional[Decimal], is_create: bool = False) -> None:
    """Completa IVA automático cuando hay neto gravado sin IVA explícito y recalcula importe_total en A/M."""
    alicuotas = (
        ("neto_gravado_21", "iva_21", Decimal("0.21")),
        ("neto_gravado_105", "iva_105", Decimal("0.105")),
        ("neto_gravado_27", "iva_27", Decimal("0.27")),
    )
    for neto_field, iva_field, tasa in alicuotas:
        neto_val = Decimal(str(getattr(db_comp, neto_field) or 0))
        iva_val = Decimal(str(getattr(db_comp, iva_field) or 0))
        if neto_val > Decimal("0.0") and iva_val == Decimal("0.0"):
            setattr(db_comp, iva_field, round(neto_val * tasa, 2))

    if db_comp.tipo_comprobante in [TipoComprobante.A, TipoComprobante.M, TipoComprobante.NOTA_DEBITO_A, TipoComprobante.NOTA_CREDITO_A]:
        calculado = sum([
            Decimal(str(db_comp.importe_no_gravado or 0)),
            Decimal(str(db_comp.importe_exento or 0)),
            Decimal(str(db_comp.neto_gravado_21 or 0)),
            Decimal(str(db_comp.neto_gravado_105 or 0)),
            Decimal(str(db_comp.neto_gravado_27 or 0)),
            Decimal(str(db_comp.iva_21 or 0)),
            Decimal(str(db_comp.iva_105 or 0)),
            Decimal(str(db_comp.iva_27 or 0)),
            Decimal(str(db_comp.percepcion_iva or 0)),
            Decimal(str(db_comp.percepcion_iibb or 0)),
            Decimal(str(db_comp.percepcion_ganancias or 0)),
            Decimal(str(db_comp.otros_impuestos or 0)),
        ])
        if importe_total_recibido is not None and abs(importe_total_recibido - calculado) <= Decimal("1.00"):
            db_comp.importe_total = importe_total_recibido
        else:
            db_comp.importe_total = calculado
    elif is_create:
        db_comp.importe_total = importe_total_recibido or Decimal("0.0")
    elif importe_total_recibido is not None:
        db_comp.importe_total = importe_total_recibido


@router.post("/comprobantes", response_model=ComprobanteResponse)
def create_comprobante(comprobante: ComprobanteCreate, db: Session = Depends(get_db)):
    db_comprobante = Comprobante(**comprobante.model_dump())
    _autocalcular_iva_y_total(db_comprobante, comprobante.importe_total, is_create=True)
    
    db.add(db_comprobante)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error al crear comprobante: {str(e)}")
    db.refresh(db_comprobante)
    # Refetch to get related proveedor and concepto
    db_comprobante = db.query(Comprobante).options(joinedload(Comprobante.proveedor), joinedload(Comprobante.concepto)).filter(Comprobante.id == db_comprobante.id).first()
    return db_comprobante

@router.put("/comprobantes/{comprobante_id}", response_model=ComprobanteResponse)
def update_comprobante(comprobante_id: int, comprobante: ComprobanteUpdate, db: Session = Depends(get_db)):
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    
    for key, value in comprobante.model_dump(exclude_unset=True).items():
        setattr(db_comprobante, key, value)
        
    _autocalcular_iva_y_total(db_comprobante, comprobante.importe_total, is_create=False)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar comprobante")
        
    db.refresh(db_comprobante)
    db_comprobante = db.query(Comprobante).options(joinedload(Comprobante.proveedor), joinedload(Comprobante.concepto)).filter(Comprobante.id == db_comprobante.id).first()
    return db_comprobante

@router.delete("/comprobantes/{comprobante_id}")
def delete_comprobante(comprobante_id: int, db: Session = Depends(get_db)):
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    
    if db_comprobante.archivo_pdf:
        # Optional: delete file
        try:
            os.remove(db_comprobante.archivo_pdf)
        except OSError:
            pass
            
    db.delete(db_comprobante)
    db.commit()
    return {"message": "Comprobante eliminado exitosamente"}

def _validar_y_preparar_cancelacion(
    db: Session,
    db_comprobante: Comprobante,
    importe_raw,
    movimiento_id: Optional[int],
    cancelacion_actual_id: Optional[int] = None,
    prev_importe: Decimal = Decimal("0.0"),
) -> tuple[Decimal, Decimal]:
    """Valida importe positivo, tope contra saldo del comprobante y saldo disponible del movimiento."""
    raw = Decimal(str(importe_raw))
    if raw <= Decimal("0.0"):
        raise HTTPException(status_code=400, detail="El importe de la cancelación debe ser mayor a 0")

    importe_cancelacion = abs(raw)
    current_cancelado = Decimal(str(db_comprobante.importe_cancelado or 0))
    nuevo_cancelado = current_cancelado - Decimal(str(prev_importe or 0)) + importe_cancelacion
    total_comp = Decimal(str(db_comprobante.importe_total or 0))

    if nuevo_cancelado > total_comp + Decimal("0.05"):
        raise HTTPException(status_code=400, detail="El importe cancelado supera el saldo pendiente del comprobante")

    if movimiento_id is not None:
        from sqlalchemy import func
        from src.database.models.finance.bancos import Movimiento
        mov = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
        if not mov:
            raise HTTPException(status_code=404, detail="Movimiento bancario no encontrado")

        q_asignado = db.query(func.sum(CancelacionComprobante.importe)).filter(
            CancelacionComprobante.movimiento_id == movimiento_id
        )
        if cancelacion_actual_id is not None:
            q_asignado = q_asignado.filter(CancelacionComprobante.id != cancelacion_actual_id)
        asignado_prev = Decimal(str(q_asignado.scalar() or 0))
        if asignado_prev + importe_cancelacion > abs(Decimal(str(mov.monto))) + Decimal("0.05"):
            raise HTTPException(status_code=400, detail="El importe supera el saldo disponible del movimiento bancario")

    return importe_cancelacion, nuevo_cancelado


def _aplicar_estado_comprobante(db_comprobante: Comprobante, nuevo_cancelado: Decimal) -> None:
    db_comprobante.importe_cancelado = nuevo_cancelado
    if db_comprobante.importe_total and nuevo_cancelado >= db_comprobante.importe_total:
        db_comprobante.estado = EstadoComprobante.PAGADO
    elif nuevo_cancelado > 0:
        db_comprobante.estado = EstadoComprobante.PARCIAL
    else:
        db_comprobante.estado = EstadoComprobante.PENDIENTE


# -------------------------------------------------------------------
# Cancelaciones de Comprobantes
# -------------------------------------------------------------------
@router.post("/comprobantes/{comprobante_id}/cancelaciones", response_model=CancelacionResponse)
def create_cancelacion(
    comprobante_id: int, 
    cancelacion: CancelacionCreate, 
    db: Session = Depends(get_db)
):
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
    importe_cancelacion, nuevo_cancelado = _validar_y_preparar_cancelacion(
        db=db,
        db_comprobante=db_comprobante,
        importe_raw=cancelacion.importe,
        movimiento_id=cancelacion.movimiento_id,
    )
            
    db_cancelacion = CancelacionComprobante(
        comprobante_id=comprobante_id,
        importe=importe_cancelacion,
        fecha_cancelacion=cancelacion.fecha_cancelacion,
        movimiento_id=cancelacion.movimiento_id
    )
    
    db.add(db_cancelacion)
    _aplicar_estado_comprobante(db_comprobante, nuevo_cancelado)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error al guardar cancelación: {str(e)}")
        
    db.refresh(db_cancelacion)
    return db_cancelacion


@router.get("/comprobantes/{comprobante_id}/cancelaciones", response_model=List[CancelacionResponse])
def get_cancelaciones(comprobante_id: int, db: Session = Depends(get_db)):
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
    from sqlalchemy.orm import joinedload
    from src.database.models.finance.bancos import Movimiento
    cancelaciones = db.query(CancelacionComprobante)\
        .options(joinedload(CancelacionComprobante.movimiento).joinedload(Movimiento.cuenta))\
        .filter(CancelacionComprobante.comprobante_id == comprobante_id)\
        .order_by(CancelacionComprobante.fecha_cancelacion.desc())\
        .all()
        
    for c in cancelaciones:
        if c.movimiento and getattr(c.movimiento, 'cuenta', None):
            c.movimiento_info = {
                "id": c.movimiento.id,
                "cuenta_nombre": c.movimiento.cuenta.nombre
            }
            
    return cancelaciones

@router.put("/cancelaciones/{cancelacion_id}", response_model=CancelacionResponse)
def update_cancelacion(cancelacion_id: int, cancelacion: CancelacionCreate, db: Session = Depends(get_db)):
    db_cancelacion = db.query(CancelacionComprobante).filter(CancelacionComprobante.id == cancelacion_id).first()
    if not db_cancelacion:
        raise HTTPException(status_code=404, detail="Cancelación no encontrada")
    
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == db_cancelacion.comprobante_id).first()
    mov_id = cancelacion.movimiento_id if 'movimiento_id' in cancelacion.model_fields_set else db_cancelacion.movimiento_id
    
    importe_cancelacion, current_cancelado = _validar_y_preparar_cancelacion(
        db=db,
        db_comprobante=db_comprobante,
        importe_raw=cancelacion.importe,
        movimiento_id=mov_id,
        cancelacion_actual_id=cancelacion_id,
        prev_importe=Decimal(str(db_cancelacion.importe)),
    )
    _aplicar_estado_comprobante(db_comprobante, current_cancelado)
    
    db_cancelacion.importe = importe_cancelacion
    db_cancelacion.fecha_cancelacion = cancelacion.fecha_cancelacion
    if 'movimiento_id' in cancelacion.model_fields_set:
        db_cancelacion.movimiento_id = cancelacion.movimiento_id
    
    db.commit()
    db.refresh(db_cancelacion)
    return db_cancelacion

@router.delete("/cancelaciones/{cancelacion_id}")
def delete_cancelacion(cancelacion_id: int, db: Session = Depends(get_db)):
    db_cancelacion = db.query(CancelacionComprobante).filter(CancelacionComprobante.id == cancelacion_id).first()
    if not db_cancelacion:
        raise HTTPException(status_code=404, detail="Cancelación no encontrada")
    
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == db_cancelacion.comprobante_id).first()
    current_cancelado = Decimal(str(db_comprobante.importe_cancelado or 0)) - Decimal(str(db_cancelacion.importe))
    _aplicar_estado_comprobante(db_comprobante, current_cancelado)
    
    db.delete(db_cancelacion)
    db.commit()
    return {"message": "Cancelación eliminada exitosamente"}

@router.post("/comprobantes/{comprobante_id}/upload")
def upload_comprobante_pdf(
    comprobante_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    from src.utils.file_validation import (
        DOCUMENT_AND_IMAGE_EXTS,
        stream_save_upload_file,
        validate_upload_file,
    )

    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
    _, ext = validate_upload_file(file, DOCUMENT_AND_IMAGE_EXTS)
        
    upload_dir = "data/uploads/comprobantes"
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"comp_{comprobante_id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    stream_save_upload_file(file, filepath)
        
    db_comprobante.archivo_pdf = filepath
    db.commit()
    db.refresh(db_comprobante)
    
    return {"message": "Archivo subido correctamente", "filepath": filepath}
