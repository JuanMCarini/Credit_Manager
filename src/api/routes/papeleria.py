import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database import get_db, SocioComercial
from src.database.models.papeleria import DocumentoPapeleria

router = APIRouter(prefix="/api/v1/papeleria", tags=["Papeleria"])

DATA_DIR = "data/papeleria"

def _ensure_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

@router.post("/upload")
def upload_document(
    socio_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validar que el socio existe si no es la empresa dueña (socio_id == 0)
    db_socio_id = socio_id if socio_id > 0 else None

    if db_socio_id is not None:
        socio = db.query(SocioComercial).filter(SocioComercial.id == db_socio_id).first()
        if not socio:
            raise HTTPException(status_code=404, detail="Socio comercial no encontrado.")

    # Validar extensión (Solo Word)
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".doc", ".docx"]:
        raise HTTPException(status_code=400, detail="Solo se permiten documentos Word (.doc, .docx).")

    _ensure_dir()
    
    # Para evitar colisiones, guardamos en data/papeleria/{db_socio_id o 0}_{filename}
    safe_filename = f"{db_socio_id or 0}_{filename}"
    file_path = os.path.join(DATA_DIR, safe_filename)

    # Si existe, lo sobreescribimos
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    # Buscar si ya existe un registro para este socio y archivo
    if db_socio_id is not None:
        doc = db.query(DocumentoPapeleria).filter(
            DocumentoPapeleria.socio_id == db_socio_id,
            DocumentoPapeleria.nombre_archivo == filename
        ).first()
    else:
        doc = db.query(DocumentoPapeleria).filter(
            DocumentoPapeleria.socio_id.is_(None),
            DocumentoPapeleria.nombre_archivo == filename
        ).first()

    if doc:
        doc.ruta_archivo = file_path
        doc.tipo_archivo = ext
        from sqlalchemy.sql import func
        doc.fecha_subida = func.now()
    else:
        doc = DocumentoPapeleria(
            socio_id=db_socio_id,
            nombre_archivo=filename,
            ruta_archivo=file_path,
            tipo_archivo=ext
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)

    return {
        "status": "success",
        "message": "Documento subido correctamente",
        "documento": {
            "id": doc.id,
            "nombre_archivo": doc.nombre_archivo
        }
    }

@router.get("/")
def list_documents(socio_id: int = None, db: Session = Depends(get_db)):
    query = db.query(DocumentoPapeleria)
    if socio_id is not None:
        if socio_id == 0:
            query = query.filter(DocumentoPapeleria.socio_id.is_(None))
        else:
            query = query.filter(DocumentoPapeleria.socio_id == socio_id)
    
    docs = query.order_by(DocumentoPapeleria.fecha_subida.desc()).all()
    
    from src.config import COMPANY_DATA
    
    result = []
    for doc in docs:
        result.append({
            "id": doc.id,
            "socio_id": doc.socio_id if doc.socio_id is not None else 0,
            "socio_nombre": doc.socio.razon_social if doc.socio else COMPANY_DATA.razon_social,
            "nombre_archivo": doc.nombre_archivo,
            "tipo_archivo": doc.tipo_archivo,
            "fecha_subida": doc.fecha_subida.isoformat() if doc.fecha_subida else None
        })
    return result

@router.get("/download/{doc_id}")
def download_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    if not os.path.exists(doc.ruta_archivo):
        raise HTTPException(status_code=404, detail="El archivo físico no existe en el servidor.")
    
    return FileResponse(
        path=doc.ruta_archivo,
        filename=doc.nombre_archivo,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    if os.path.exists(doc.ruta_archivo):
        try:
            os.remove(doc.ruta_archivo)
        except Exception as e:
            # Continuamos aunque falle borrar el archivo físico (podría estar bloqueado)
            pass
            
    db.delete(doc)
    db.commit()
    
    return {"status": "success", "message": "Documento eliminado correctamente"}
