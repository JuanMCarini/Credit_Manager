import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db, SocioComercial, Credito, Cliente
from src.database.models.papeleria import DocumentoPapeleria, DocumentoVariable
from src.config import COMPANY_DATA

class VariableItem(BaseModel):
    placeholder: str
    system_field: str

class VariablesRequest(BaseModel):
    variables: List[VariableItem]

class ReorderItem(BaseModel):
    id: int
    orden: int

class ReorderRequest(BaseModel):
    documentos: List[ReorderItem]

SYSTEM_FIELDS = [
    {"value": "cliente.nombre", "label": "Cliente - Nombre Completo"},
    {"value": "cliente.dni", "label": "Cliente - DNI"},
    {"value": "cliente.cuil", "label": "Cliente - CUIL"},
    {"value": "cliente.domicilio", "label": "Cliente - Domicilio"},
    {"value": "cliente.cbu", "label": "Cliente - CBU"},
    {"value": "cliente.localidad", "label": "Cliente - Localidad"},
    {"value": "cliente.provincia", "label": "Cliente - Provincia"},
    {"value": "cliente.nacionalidad", "label": "Cliente - País / Nacionalidad"},
    {"value": "credito.monto_otorgado", "label": "Crédito - Monto Otorgado"},
    {"value": "credito.fecha_alta", "label": "Crédito - Fecha Alta"},
    {"value": "credito.fecha_emision_dia", "label": "Crédito - Fecha Emisión (Día)"},
    {"value": "credito.fecha_emision_mes_letras", "label": "Crédito - Fecha Emisión (Mes Letras)"},
    {"value": "credito.fecha_emision_anio", "label": "Crédito - Fecha Emisión (Año)"},
    {"value": "credito.cuotas", "label": "Crédito - Cantidad Cuotas"},
    {"value": "empresa.razon_social", "label": "Empresa - Razón Social"},
    {"value": "empresa.cuit", "label": "Empresa - CUIT"},
    {"value": "socio.razon_social", "label": "Socio Comercial - Razón Social"},
]

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
    
    docs = query.order_by(DocumentoPapeleria.orden.asc(), DocumentoPapeleria.fecha_subida.desc()).all()
    
    from src.config import COMPANY_DATA
    
    result = []
    for doc in docs:
        result.append({
            "id": doc.id,
            "socio_id": doc.socio_id if doc.socio_id is not None else 0,
            "socio_nombre": doc.socio.razon_social if doc.socio else COMPANY_DATA.razon_social,
            "nombre_archivo": doc.nombre_archivo,
            "tipo_archivo": doc.tipo_archivo,
            "orden": doc.orden,
            "fecha_subida": doc.fecha_subida.isoformat() if doc.fecha_subida else None
        })
    return result

from pydantic import BaseModel
class UpdateSocioPayload(BaseModel):
    socio_id: str | int | None

@router.patch("/{doc_id}/socio")
def update_document_socio(doc_id: int, payload: UpdateSocioPayload, db: Session = Depends(get_db)):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    socio_id_val = None
    if str(payload.socio_id).strip() != "" and str(payload.socio_id) != "0":
        socio_id_val = int(payload.socio_id)
        
    if socio_id_val is not None:
        from src.database.models import Socio
        socio_exist = db.query(Socio).filter(Socio.id == socio_id_val).first()
        if not socio_exist:
            raise HTTPException(status_code=400, detail="El socio especificado no existe")

    doc.socio_id = socio_id_val
    db.commit()
    return {"status": "success", "message": "Socio actualizado correctamente"}

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

@router.put("/{doc_id}/file")
def replace_document_file(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".doc", ".docx"]:
        raise HTTPException(status_code=400, detail="Solo se permiten documentos Word (.doc, .docx).")

    _ensure_dir()
    db_socio_id = doc.socio_id if doc.socio_id else 0
    safe_filename = f"{db_socio_id}_{filename}"
    file_path = os.path.join(DATA_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")
        
    if doc.ruta_archivo != file_path and os.path.exists(doc.ruta_archivo):
        try:
            os.remove(doc.ruta_archivo)
        except:
            pass

    doc.ruta_archivo = file_path
    doc.nombre_archivo = filename
    doc.tipo_archivo = ext
    
    db.commit()
    return {"status": "success", "message": "Archivo reemplazado correctamente"}

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

@router.get("/system_fields")
def get_system_fields():
    return SYSTEM_FIELDS

@router.get("/{doc_id}/variables")
def get_document_variables(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    return [{"id": v.id, "placeholder": v.placeholder, "system_field": v.system_field} for v in doc.variables]

@router.post("/{doc_id}/variables")
def save_document_variables(doc_id: int, request: VariablesRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    # Delete existing
    db.query(DocumentoVariable).filter(DocumentoVariable.documento_id == doc_id).delete()
    
    # Add new
    for var_req in request.variables:
        new_var = DocumentoVariable(
            documento_id=doc_id,
            placeholder=var_req.placeholder,
            system_field=var_req.system_field
        )
        db.add(new_var)
    
    db.commit()
    return {"status": "success", "message": "Variables guardadas correctamente"}

@router.post("/reorder")
def reorder_documents(request: ReorderRequest, db: Session = Depends(get_db)):
    for item in request.documentos:
        doc = db.query(DocumentoPapeleria).filter(DocumentoPapeleria.id == item.id).first()
        if doc:
            doc.orden = item.orden
    
    db.commit()
    return {"status": "success", "message": "Orden actualizado correctamente"}

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def resolve_system_field(credito: Credito, field: str):
    if field == "cliente.nombre":
        return f"{credito.cliente.nombre} {credito.cliente.apellido}"
    elif field == "cliente.dni":
        return credito.cliente.documento
    elif field == "cliente.cuil":
        return credito.cliente.cuil
    elif field == "cliente.domicilio":
        return f"{credito.cliente.calle or ''} {credito.cliente.calle_nro or ''} {credito.cliente.localidad or ''}".strip()
    elif field == "cliente.cbu":
        return credito.cliente.cbu or ""
    elif field == "cliente.localidad":
        return credito.cliente.localidad or ""
    elif field == "cliente.provincia":
        return credito.cliente.provincia.nombre if credito.cliente.provincia else ""
    elif field == "cliente.nacionalidad":
        return credito.cliente.nacionalidad or ""
    elif field == "credito.monto_otorgado":
        return str(credito.capital)
    elif field == "credito.fecha_alta":
        return credito.fecha_emision.strftime("%d/%m/%Y") if credito.fecha_emision else ""
    elif field == "credito.fecha_emision_dia":
        return str(credito.fecha_emision.day) if credito.fecha_emision else ""
    elif field == "credito.fecha_emision_mes_letras":
        if credito.fecha_emision:
            return MESES[credito.fecha_emision.month - 1]
        return ""
    elif field == "credito.fecha_emision_anio":
        return str(credito.fecha_emision.year) if credito.fecha_emision else ""
    elif field == "credito.cuotas":
        return str(len(credito.cuotas))
    elif field == "empresa.razon_social":
        return COMPANY_DATA.razon_social
    elif field == "empresa.cuit":
        return COMPANY_DATA.cuit
    elif field == "socio.razon_social":
        return credito.socio_originador.razon_social if credito.socio_originador else ""
    return ""

@router.post("/generar_por_credito/{credito_id}")
def generar_papeleria_credito(credito_id: int, db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado.")
    
    socio_ids = [None]
    
    # Extraer socios de la tasa y comisión
    if credito.comision:
        if credito.comision.socio_originador_id:
            socio_ids.append(credito.comision.socio_originador_id)
        if credito.comision.socio_intermediario_id:
            socio_ids.append(credito.comision.socio_intermediario_id)
        if credito.comision.gasto_1_socio_id:
            socio_ids.append(credito.comision.gasto_1_socio_id)
        if credito.comision.gasto_2_socio_id:
            socio_ids.append(credito.comision.gasto_2_socio_id)

    # Si por alguna razón tiene originador directo pero no está en la lista (caso legado)
    if credito.socio_originador_id and credito.socio_originador_id not in socio_ids:
        socio_ids.append(credito.socio_originador_id)

    # Filtro combinado porque in_() con SQL no funciona para NULL
    from sqlalchemy import or_
    valid_ids = [s for s in socio_ids if s is not None]
    
    docs = db.query(DocumentoPapeleria).filter(
        or_(
            DocumentoPapeleria.socio_id.is_(None),
            DocumentoPapeleria.socio_id.in_(valid_ids) if valid_ids else False
        )
    ).order_by(
        DocumentoPapeleria.socio_id.isnot(None),
        DocumentoPapeleria.orden.asc()
    ).all()

    if not docs:
        raise HTTPException(status_code=400, detail="No hay documentos de papelería configurados.")

    import tempfile
    from pypdf import PdfWriter
    from src.logic.legajos import process_document

    merger = PdfWriter()
    temp_files = []
    output_dir = "data/legajos"
    os.makedirs(output_dir, exist_ok=True)
    final_pdf_path = os.path.join(output_dir, f"credito_{credito_id}.pdf")

    import pythoncom

    try:
        try:
            pythoncom.CoInitialize()
            for doc in docs:
                data = {}
                for var in doc.variables:
                    data[var.placeholder] = resolve_system_field(credito, var.system_field)

                fd, temp_pdf = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                os.remove(temp_pdf)
                temp_files.append(temp_pdf)
                
                process_document(doc.ruta_archivo, temp_pdf, data)
                merger.append(temp_pdf)

            merger.write(final_pdf_path)
            merger.close()

        finally:
            pythoncom.CoUninitialize()
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
    except Exception as e:
        import traceback
        error_msg = f"Error interno: {str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)

    return FileResponse(
        path=final_pdf_path,
        filename=f"Legajo_Credito_{credito_id}.pdf",
        media_type='application/pdf'
    )
