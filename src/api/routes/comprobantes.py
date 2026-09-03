from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List
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

@router.post("/comprobantes", response_model=ComprobanteResponse)
def create_comprobante(comprobante: ComprobanteCreate, db: Session = Depends(get_db)):
    from decimal import Decimal
    db_comprobante = Comprobante(**comprobante.model_dump())
    
    def _calc_total(comp):
        return sum([
            comp.importe_no_gravado or Decimal('0.0'),
            comp.importe_exento or Decimal('0.0'),
            comp.neto_gravado_21 or Decimal('0.0'),
            comp.neto_gravado_105 or Decimal('0.0'),
            comp.neto_gravado_27 or Decimal('0.0'),
            comp.iva_21 or Decimal('0.0'),
            comp.iva_105 or Decimal('0.0'),
            comp.iva_27 or Decimal('0.0'),
            comp.percepcion_iva or Decimal('0.0'),
            comp.percepcion_iibb or Decimal('0.0'),
            comp.percepcion_ganancias or Decimal('0.0'),
            comp.otros_impuestos or Decimal('0.0')
        ])
        
    if db_comprobante.tipo_comprobante in [TipoComprobante.A, TipoComprobante.M, TipoComprobante.NOTA_DEBITO_A, TipoComprobante.NOTA_CREDITO_A]:
        calculado = _calc_total(db_comprobante)
        if comprobante.importe_total is not None and abs(comprobante.importe_total - calculado) <= Decimal('1.00'):
            db_comprobante.importe_total = comprobante.importe_total
        else:
            db_comprobante.importe_total = calculado
    else:
        db_comprobante.importe_total = comprobante.importe_total or Decimal('0.0')
    
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
        
    from decimal import Decimal
    if db_comprobante.tipo_comprobante in [TipoComprobante.A, TipoComprobante.M, TipoComprobante.NOTA_DEBITO_A, TipoComprobante.NOTA_CREDITO_A]:
        calculado = sum([
            db_comprobante.importe_no_gravado or Decimal('0.0'),
            db_comprobante.importe_exento or Decimal('0.0'),
            db_comprobante.neto_gravado_21 or Decimal('0.0'),
            db_comprobante.neto_gravado_105 or Decimal('0.0'),
            db_comprobante.neto_gravado_27 or Decimal('0.0'),
            db_comprobante.iva_21 or Decimal('0.0'),
            db_comprobante.iva_105 or Decimal('0.0'),
            db_comprobante.iva_27 or Decimal('0.0'),
            db_comprobante.percepcion_iva or Decimal('0.0'),
            db_comprobante.percepcion_iibb or Decimal('0.0'),
            db_comprobante.percepcion_ganancias or Decimal('0.0'),
            db_comprobante.otros_impuestos or Decimal('0.0')
        ])
        if comprobante.importe_total is not None and abs(comprobante.importe_total - calculado) <= Decimal('1.00'):
            db_comprobante.importe_total = comprobante.importe_total
        else:
            db_comprobante.importe_total = calculado
    else:
        if comprobante.importe_total is not None:
            db_comprobante.importe_total = comprobante.importe_total
    
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

# -------------------------------------------------------------------
# Cancelaciones de Comprobantes
# -------------------------------------------------------------------
@router.post("/comprobantes/{comprobante_id}/cancelaciones", response_model=CancelacionResponse)
def create_cancelacion(
    comprobante_id: int, 
    cancelacion: CancelacionCreate, 
    db: Session = Depends(get_db)
):
    from decimal import Decimal
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
    # Ajustar el signo del importe según el movimiento bancario si existe
    importe_cancelacion = Decimal(str(cancelacion.importe))
    if cancelacion.movimiento_id:
        from src.database.models.finance.bancos import Movimiento
        mov = db.query(Movimiento).filter(Movimiento.id == cancelacion.movimiento_id).first()
        if mov and mov.monto < 0:
            importe_cancelacion = -abs(importe_cancelacion)
        else:
            importe_cancelacion = abs(importe_cancelacion)
            
    db_cancelacion = CancelacionComprobante(
        comprobante_id=comprobante_id,
        importe=importe_cancelacion,
        fecha_cancelacion=cancelacion.fecha_cancelacion,
        movimiento_id=cancelacion.movimiento_id
    )
    
    db.add(db_cancelacion)
    
    # Update importe_cancelado of parent Comprobante
    current_cancelado = db_comprobante.importe_cancelado or Decimal('0.0')
    nuevo_cancelado = current_cancelado + importe_cancelacion
    db_comprobante.importe_cancelado = nuevo_cancelado
    if db_comprobante.importe_total and nuevo_cancelado >= db_comprobante.importe_total:
        db_comprobante.estado = EstadoComprobante.PAGADO
    elif nuevo_cancelado > 0:
        db_comprobante.estado = EstadoComprobante.PARCIAL
    else:
        db_comprobante.estado = EstadoComprobante.PENDIENTE
    
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
    
    # Ajustar el signo del importe según el movimiento bancario si existe
    from decimal import Decimal
    importe_cancelacion = Decimal(str(cancelacion.importe))
    mov_id = cancelacion.movimiento_id if hasattr(cancelacion, 'movimiento_id') else db_cancelacion.movimiento_id
    if mov_id:
        from src.database.models.finance.bancos import Movimiento
        mov = db.query(Movimiento).filter(Movimiento.id == mov_id).first()
        if mov and mov.monto < 0:
            importe_cancelacion = -abs(importe_cancelacion)
        else:
            importe_cancelacion = abs(importe_cancelacion)
            
    # Update importe_cancelado of parent Comprobante
    current_cancelado = db_comprobante.importe_cancelado or Decimal('0.0')
    current_cancelado = current_cancelado - Decimal(str(db_cancelacion.importe)) + importe_cancelacion
    db_comprobante.importe_cancelado = current_cancelado
    if db_comprobante.importe_total and current_cancelado >= db_comprobante.importe_total:
        db_comprobante.estado = EstadoComprobante.PAGADO
    elif current_cancelado > 0:
        db_comprobante.estado = EstadoComprobante.PARCIAL
    else:
        db_comprobante.estado = EstadoComprobante.PENDIENTE
    
    db_cancelacion.importe = importe_cancelacion
    db_cancelacion.fecha_cancelacion = cancelacion.fecha_cancelacion
    if hasattr(cancelacion, 'movimiento_id'):
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
    
    # Update importe_cancelado of parent Comprobante
    from decimal import Decimal
    current_cancelado = db_comprobante.importe_cancelado or Decimal('0.0')
    current_cancelado = current_cancelado - Decimal(str(db_cancelacion.importe))
    db_comprobante.importe_cancelado = current_cancelado
    if db_comprobante.importe_total and current_cancelado >= db_comprobante.importe_total:
        db_comprobante.estado = EstadoComprobante.PAGADO
    elif current_cancelado > 0:
        db_comprobante.estado = EstadoComprobante.PARCIAL
    else:
        db_comprobante.estado = EstadoComprobante.PENDIENTE
    
    db.delete(db_cancelacion)
    db.commit()
    return {"message": "Cancelación eliminada exitosamente"}

@router.post("/comprobantes/{comprobante_id}/upload")

def upload_comprobante_pdf(
    comprobante_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    db_comprobante = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not db_comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
    if not file.filename.endswith(".pdf") and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF o imágenes")
        
    upload_dir = "data/uploads/comprobantes"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"comp_{comprobante_id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_comprobante.archivo_pdf = filepath
    db.commit()
    db.refresh(db_comprobante)
    
    return {"message": "Archivo subido correctamente", "filepath": filepath}
