from typing import Any, Dict, List, Optional, Tuple
from datetime import date
import os
import shutil
import zipfile
import re
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from pypdf import PdfWriter, PdfReader
from PIL import Image

from src.database import get_db, Credito, Transferencia
from src.database.models import EstadoCredito, Cuota, DocumentoLegajo
from src.api.schemas.creditos import CreditoCreate, CreditoEstadoUpdate, DocumentoLegajoOut
from src.logic.origination import LoanOriginator
from src.logic.amortization import AmortizationEngine

router = APIRouter(tags=["Créditos"])

@router.get("/api/v1/creditos/simular-cuotas")
def simular_cuotas(
    credito_id: int = Query(..., description="ID identificador del crédito de simulación"),
    capital: float = Query(..., description="Monto de capital a amortizar"),
    tna_c_iva: float = Query(..., description="Tasa Nominal Anual con IVA incluido"),
    plazo: int = Query(..., description="Cantidad de meses/cuotas del crédito"),
    fecha_emision: date = Query(..., description="Fecha de emisión del crédito (YYYY-MM-DD)"),
    dia_vencimiento: int = Query(28, description="Día del mes para el vencimiento"),
    gracia: int = Query(2, description="Meses de gracia aplicables"),
    tasa_iva: float = Query(0.21, description="Alícuota impositiva (ej. 0.21)"),
    dia_corte: int = Query(28, description="Día de corte del crédito"),
) -> List[Dict[str, Any]]:
    try:
        cuotas_obj = AmortizationEngine.generate_french_schedule(
            credito_id=credito_id,
            capital=capital,
            tna_c_iva=tna_c_iva,
            plazo=plazo,
            fecha_emision=fecha_emision,
            dia_vencimiento=dia_vencimiento,
            gracia=gracia,
            tasa_iva=tasa_iva,
            dia_corte=dia_corte,
        )

        return [
            {
                "credito_id": c.credito_id,
                "nro_cuota": c.nro_cuota,
                "fecha_vencimiento": c.fecha_vencimiento.strftime("%Y-%m-%d") if c.fecha_vencimiento else None,
                "capital": c.capital,
                "interes": c.interes,
                "iva": c.iva,
            }
            for c in cuotas_obj
        ]
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/api/v1/creditos/originacion")
def create_credito(
    credito_data: CreditoCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        originator = LoanOriginator(db_session=db)
        nuevo_credito = originator.originate(
            client_cuil=credito_data.cliente_cuil,
            capital=credito_data.capital,
            tna_c_iva=credito_data.tna_c_iva,
            term=credito_data.plazo,
            partner_id=credito_data.socio_originador_id,
            issuance_date=credito_data.fecha_emision,
            due_day=credito_data.dia_vencimiento,
            type=credito_data.tipo_credito,
            comision_id=credito_data.comision_id,
            transferencias_data=credito_data.transferencias
        )
        return {
            "status": "success",
            "message": "Crédito originado y cuotas generadas exitosamente.",
            "credito_id": nuevo_credito.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error originando el crédito: {str(e)}")

@router.patch("/api/v1/creditos/{credito_id}/estado")
def update_credito_estado(credito_id: int, data: CreditoEstadoUpdate, db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    
    try:
        nuevo_estado = EstadoCredito(data.estado.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido.")
        
    credito.estado = nuevo_estado
    db.commit()
    return {"status": "success", "message": "Estado actualizado"}

@router.get("/api/v1/creditos/{credito_id}/cuotas")
def get_credito_cuotas(credito_id: int, db: Session = Depends(get_db)):
    cuotas = db.query(Cuota).options(joinedload(Cuota.cobranzas)).filter(Cuota.credito_id == credito_id).order_by(Cuota.nro_cuota).all()
    
    result = []
    for c in cuotas:
        total_esperado = round(c.capital + c.interes + c.iva, 2)
        total_cobrado = 0.0
        detalle_cobranzas = []
        
        sorted_cobranzas = sorted(c.cobranzas, key=lambda cob: cob.fecha)
        for cob in sorted_cobranzas:
            tot = round(cob.capital + cob.interes + cob.iva, 2)
            total_cobrado += tot
            detalle_cobranzas.append({
                "id": cob.id,
                "fecha": cob.fecha.strftime("%d/%m/%Y"),
                "tipo": cob.tipo_cobranza.value if hasattr(cob.tipo_cobranza, "value") else str(cob.tipo_cobranza),
                "capital": round(cob.capital, 2),
                "interes": round(cob.interes, 2),
                "iva": round(cob.iva, 2),
                "total": tot
            })
            
        total_cobrado = round(total_cobrado, 2)
        saldo = round(total_esperado - total_cobrado, 2)
        
        result.append({
            "nro_cuota": c.nro_cuota,
            "vencimiento": c.fecha_vencimiento.strftime("%d/%m/%Y"),
            "capital": round(c.capital, 2),
            "interes": round(c.interes, 2),
            "iva": round(c.iva, 2),
            "total_esperado": total_esperado,
            "total_cobrado": total_cobrado,
            "saldo_pendiente": saldo,
            "estado": c.estado.value,
            "detalle_cobranzas": detalle_cobranzas
        })
        
    return result

@router.get("/api/v1/creditos/{credito_id}/transferencias")
def get_credito_transferencias(credito_id: int, db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
        
    transferencias = db.query(Transferencia).filter(Transferencia.credito_id == credito_id).all()
    
    result = []
    for t in transferencias:
        result.append({
            "id": t.id,
            "cbu": t.cbu,
            "monto": float(t.monto),
            "cuit": t.cuit,
            "razon_social": t.razon_social
        })
    return result

@router.get("/api/v1/creditos")
def get_creditos_list(db: Session = Depends(get_db)):
    creditos = db.query(Credito).options(joinedload(Credito.cliente), joinedload(Credito.socio_originador)).all()
    result = []
    for c in creditos:
        nombre_cliente = f"{c.cliente.apellido}, {c.cliente.nombre}" if c.cliente else "-"
        origen = c.origen.value if hasattr(c.origen, 'value') else str(c.origen)
        socio = c.socio_originador.razon_social if c.socio_originador else "-"
        result.append({
            "ID": c.id,
            "ID Externo": c.id_externo or "-",
            "Cliente CUIL": c.cliente_cuil,
            "Cliente Nombre": nombre_cliente,
            "Origen": origen,
            "Socio Originador": socio,
            "Capital": float(c.capital),
            "TNA con IVA": float(c.tna_c_iva),
            "Plazo": c.plazo,
            "Fecha Emisión": c.fecha_emision.strftime("%Y-%m-%d"),
            "Estado": c.estado.value if c.estado else "-",
            "Tipo Crédito": c.tipo_credito.value if c.tipo_credito else "-",
            "Día Vto": c.dia_vencimiento
        })
    return result

@router.delete("/api/v1/creditos/{credito_id}")
def delete_credito(credito_id: int, db: Session = Depends(get_db)):
    credito = db.query(Credito).options(joinedload(Credito.cuotas).joinedload(Cuota.cobranzas)).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
        
    if credito.estado != EstadoCredito.APROBADO:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede eliminar un crédito si su estado es APROBADO."
        )
        
    has_cobranzas = any(len(cuota.cobranzas) > 0 for cuota in credito.cuotas)
    if has_cobranzas:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar el crédito porque ya tiene cobranzas asociadas."
        )
        
    try:
        db.delete(credito)
        db.commit()
        return {"status": "success", "message": "Crédito eliminado exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando el crédito: {str(e)}")

# --- LEGAJO DOCUMENTOS ENDPOINTS ---

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = os.path.join(project_root, "data", "uploads", "legajos")
@router.post("/api/v1/creditos/{credito_id}/documentos", response_model=DocumentoLegajoOut)
async def upload_documento(credito_id: int, file: UploadFile = File(...), transferencia_id: Optional[int] = Form(None), db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
        
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{credito_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    nuevo_doc = DocumentoLegajo(
        credito_id=credito_id,
        nombre_archivo=file.filename,
        ruta_archivo=file_path,
        tipo_archivo=file.content_type,
        transferencia_id=transferencia_id
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)

    if credito.estado in (EstadoCredito.APROBADO, "APROBADO", "EstadoCredito.APROBADO"):
        transferencias = db.query(Transferencia).filter(Transferencia.credito_id == credito_id).all()
        if transferencias:
            todas_con_comprobante = True
            for t in transferencias:
                doc_count = db.query(DocumentoLegajo).filter(DocumentoLegajo.transferencia_id == t.id).count()
                if doc_count == 0:
                    todas_con_comprobante = False
                    break
            
            if todas_con_comprobante:
                db.query(Credito).filter(Credito.id == credito_id).update({"estado": EstadoCredito.ACTIVO.name})
                db.commit()
                db.refresh(credito)

    return nuevo_doc

@router.get("/api/v1/creditos/{credito_id}/documentos", response_model=List[DocumentoLegajoOut])
def get_documentos(credito_id: int, db: Session = Depends(get_db)):
    docs = db.query(DocumentoLegajo).filter(DocumentoLegajo.credito_id == credito_id).all()
    return docs

@router.delete("/api/v1/creditos/{credito_id}/documentos/{doc_id}")
def delete_documento(credito_id: int, doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentoLegajo).filter(DocumentoLegajo.id == doc_id, DocumentoLegajo.credito_id == credito_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    basename = os.path.basename(doc.ruta_archivo.replace('\\', '/'))
    full_path = os.path.join(UPLOAD_DIR, basename)
    
    if os.path.exists(full_path):
        os.remove(full_path)
        
    db.delete(doc)
    db.commit()
    return {"status": "success", "message": "Documento eliminado"}

@router.get("/api/v1/creditos/{credito_id}/documentos/merged/download")
def download_merged_pdf(credito_id: int, db: Session = Depends(get_db)):
    docs = db.query(DocumentoLegajo).filter(DocumentoLegajo.credito_id == credito_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail="No hay documentos para este crédito")

    merger = PdfWriter()
    
    for doc in docs:
        basename = os.path.basename(doc.ruta_archivo.replace('\\', '/'))
        full_path = os.path.join(UPLOAD_DIR, basename)
        
        if not os.path.exists(full_path):
            continue
            
        if doc.tipo_archivo.startswith('image/'):
            try:
                img = Image.open(full_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_pdf_io = BytesIO()
                img.save(img_pdf_io, format='PDF')
                img_pdf_io.seek(0)
                
                reader = PdfReader(img_pdf_io)
                merger.append(reader)
            except Exception as e:
                print(f"Error converting image {full_path}: {e}")
        elif doc.tipo_archivo == 'application/pdf' or doc.nombre_archivo.lower().endswith('.pdf'):
            try:
                merger.append(full_path)
            except Exception as e:
                print(f"Error appending PDF {full_path}: {e}")
                
    output_pdf = BytesIO()
    merger.write(output_pdf)
    
    return Response(
        content=output_pdf.getvalue(), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=legajo_credito_{credito_id}.pdf"}
    )

@router.get("/api/v1/creditos/{credito_id}/documentos/{doc_id}/download")
def download_documento(credito_id: int, doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentoLegajo).filter(DocumentoLegajo.id == doc_id, DocumentoLegajo.credito_id == credito_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    basename = os.path.basename(doc.ruta_archivo.replace('\\', '/'))
    full_path = os.path.join(UPLOAD_DIR, basename)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="El archivo físico no existe")
        
    return FileResponse(full_path, filename=doc.nombre_archivo)

@router.post("/api/v1/creditos/procesos/upload-batch")
async def upload_batch_documentos(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    procesados = []
    errores = []

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Pre-fetch all credits to match efficiently against filenames
    creditos_bd = db.query(Credito.id, Credito.id_externo).all()

    def process_file_logic(filename: str, file_bytes: bytes, content_type: str = "application/octet-stream"):
        try:
            name_without_ext = os.path.splitext(filename)[0]
            # 1. Match Transferencia -> T-{ID}-{NUM}.ext (tolerates spaces)
            transfer_match = re.search(r"^T\s*-\s*(.+?)\s*-\s*(\d+)$", name_without_ext, re.IGNORECASE)
            
            credito = None
            transferencia = None

            if transfer_match:
                cred_id_str = transfer_match.group(1)
                transf_index_str = transfer_match.group(2)
                transf_index = int(transf_index_str)

                # Find credit
                if cred_id_str.isdigit():
                    credito = db.query(Credito).filter(or_(Credito.id == int(cred_id_str), Credito.id_externo == cred_id_str)).first()
                else:
                    credito = db.query(Credito).filter(Credito.id_externo == cred_id_str).first()

                if not credito:
                    errores.append({"archivo": filename, "error": f"Crédito no encontrado para '{cred_id_str}'"})
                    return

                # Find transfer
                transferencias = db.query(Transferencia).filter(Transferencia.credito_id == credito.id).order_by(Transferencia.id).all()
                if 1 <= transf_index <= len(transferencias):
                    transferencia = transferencias[transf_index - 1]
                else:
                    errores.append({"archivo": filename, "error": f"Transferencia índice {transf_index} no válida para crédito {credito.id}"})
                    return

            else:
                # 2. Extract potential IDs from filename
                posibles_creditos = set()
                
                for c_id, c_id_ext in creditos_bd:
                    # Check by ID using word boundaries
                    if re.search(rf'\b{c_id}\b', name_without_ext):
                        posibles_creditos.add(c_id)
                    # Check by ID_externo
                    if c_id_ext and str(c_id_ext) in name_without_ext:
                        posibles_creditos.add(c_id)
                
                if len(posibles_creditos) == 1:
                    credito_id_encontrado = list(posibles_creditos)[0]
                    credito = db.query(Credito).filter(Credito.id == credito_id_encontrado).first()
                elif len(posibles_creditos) > 1:
                    errores.append({"archivo": filename, "error": f"Nombre ambiguo: coincide con {len(posibles_creditos)} créditos distintos ({list(posibles_creditos)})"})
                    return
                else:
                    errores.append({"archivo": filename, "error": "No se pudo inferir el ID de crédito en el nombre del archivo"})
                    return

            # File save
            file_path = os.path.join(UPLOAD_DIR, f"{credito.id}_{filename}")
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            nuevo_doc = DocumentoLegajo(
                credito_id=credito.id,
                nombre_archivo=filename,
                ruta_archivo=file_path,
                tipo_archivo=content_type,
                transferencia_id=transferencia.id if transferencia else None
            )
            db.add(nuevo_doc)
            
            # Check state transition to ACTIVO
            if credito.estado in (EstadoCredito.APROBADO, "APROBADO", "EstadoCredito.APROBADO"):
                transf_todas = db.query(Transferencia).filter(Transferencia.credito_id == credito.id).all()
                if transf_todas:
                    todas_con_comprobante = True
                    # We might not have committed the new_doc yet, so check if all *other* transferencias have docs
                    for t in transf_todas:
                        if transferencia and t.id == transferencia.id:
                            continue # we are adding it right now
                        doc_count = db.query(DocumentoLegajo).filter(DocumentoLegajo.transferencia_id == t.id).count()
                        if doc_count == 0:
                            todas_con_comprobante = False
                            break
                    
                    if todas_con_comprobante:
                        db.query(Credito).filter(Credito.id == credito.id).update({"estado": EstadoCredito.ACTIVO.name})
            
            db.commit()
            procesados.append({"archivo": filename, "credito_id": credito.id, "transferencia_id": transferencia.id if transferencia else None})
            
        except Exception as e:
            db.rollback()
            errores.append({"archivo": filename, "error": str(e)})

    for file in files:
        if file.filename.lower().endswith(".zip"):
            try:
                content = await file.read()
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    for zip_info in zf.infolist():
                        if not zip_info.is_dir() and not zip_info.filename.startswith("__MACOSX/") and not zip_info.filename.startswith("."):
                            extracted_bytes = zf.read(zip_info.filename)
                            base_name = os.path.basename(zip_info.filename)
                            if base_name:
                                process_file_logic(base_name, extracted_bytes)
            except zipfile.BadZipFile:
                errores.append({"archivo": file.filename, "error": "El archivo ZIP es inválido o está corrupto"})
            except Exception as e:
                errores.append({"archivo": file.filename, "error": f"Error extrayendo ZIP: {str(e)}"})
        else:
            file_bytes = await file.read()
            process_file_logic(file.filename, file_bytes, file.content_type)

    return {"procesados": procesados, "errores": errores}
