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
from src.database.models import EstadoCredito, Cuota, DocumentoLegajo, EstadoCuota
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


@router.post("/api/v1/creditos/originacion/preview_legajo")
def preview_legajo(
    credito_data: CreditoCreate,
    db: Session = Depends(get_db)
):
    try:
        # Savepoint
        db.begin_nested()
        
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
            id_externo=credito_data.id_externo,
            transferencias_data=credito_data.transferencias,
            commit=False  # Do not commit inside originate
        )
        
        # Generar PDF en disco usando el helper
        from src.api.routes.papeleria import _generar_pdf_for_credito
        from fastapi.responses import FileResponse
        
        pdf_path = _generar_pdf_for_credito(nuevo_credito, db)
        
        # Rollback all db changes (the credit vanishes from db)
        db.rollback()
        
        return FileResponse(
            path=pdf_path,
            filename=f"Preview_Legajo_{credito_data.cliente_cuil}.pdf",
            media_type='application/pdf'
        )
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        import traceback
        error_msg = f"Error generando previsualización: {str(e)}\n\n{traceback.format_exc()}"
        with open("error_preview.txt", "w") as f:
            f.write(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/api/v1/creditos/originacion")
def create_credito(
    credito_data: CreditoCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Validación RePET antes de la originación
    from src.database.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.cuil == credito_data.cliente_cuil).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="El cliente especificado no existe.")
        
    from src.services.repet import screen_person
    import logging
    logger = logging.getLogger(__name__)
    full_name = f"{cliente.nombre} {cliente.apellido}"
    
    try:
        repet_result = screen_person(db, full_name=full_name)
        if repet_result.get("status") == "ALERT":
            cliente.repet = True
            db.commit()
    except Exception as e:
        logger.error(f"Error interno en screening RePET (alta crédito): {str(e)}")
        # Si la API falla, permitimos continuar y completar manualmente, según requerimiento.
        
    if getattr(cliente, 'repet', False):
        raise HTTPException(
            status_code=403, 
            detail="Operación denegada: El cliente se encuentra registrado en el RePET."
        )

    # 2. Originación del Crédito
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
            id_externo=credito_data.id_externo,
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

@router.patch("/api/v1/creditos/{credito_id:int}/estado")
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

@router.get("/api/v1/creditos/{credito_id:int}/cuotas")
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

@router.get("/api/v1/creditos/{credito_id:int}/transferencias")
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
def get_creditos_list(fecha_corte: Optional[date] = Query(None, description="Fecha de corte para calcular mora"), db: Session = Depends(get_db)):
    if fecha_corte is None:
        fecha_corte = date.today()
        
    creditos = db.query(Credito).options(
        joinedload(Credito.cliente), 
        joinedload(Credito.socio_originador),
        joinedload(Credito.cuotas).joinedload(Cuota.cobranzas)
    ).all()
    result = []
    for c in creditos:
        saldo_mora = 0.0
        dias_mora = 0
        min_vencimiento_mora = None

        for cuota in c.cuotas:
            if cuota.estado == EstadoCuota.NO_COMPRADA:
                continue
            if cuota.fecha_vencimiento <= fecha_corte:
                c_capital = float(cuota.capital) if cuota.capital is not None else 0.0
                c_interes = float(cuota.interes) if cuota.interes is not None else 0.0
                c_iva = float(cuota.iva) if cuota.iva is not None else 0.0
                total_esperado = round(c_capital + c_interes + c_iva, 2)
                
                total_cobrado = 0.0
                for cob in cuota.cobranzas:
                    cob_cap = float(cob.capital) if cob.capital is not None else 0.0
                    cob_int = float(cob.interes) if cob.interes is not None else 0.0
                    cob_iva = float(cob.iva) if cob.iva is not None else 0.0
                    total_cobrado += round(cob_cap + cob_int + cob_iva, 2)
                    
                total_cobrado = round(total_cobrado, 2)
                saldo_pendiente = round(total_esperado - total_cobrado, 2)
                if saldo_pendiente > 0.01: # Use 0.01 to handle minor float differences
                    saldo_mora += float(saldo_pendiente)
                    if min_vencimiento_mora is None or cuota.fecha_vencimiento < min_vencimiento_mora:
                        min_vencimiento_mora = cuota.fecha_vencimiento
        
        if min_vencimiento_mora:
            dias_mora = (fecha_corte - min_vencimiento_mora).days
            if dias_mora < 0:
                dias_mora = 0

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
            "Capital": float(c.capital) if c.capital is not None else 0.0,
            "TNA con IVA": float(c.tna_c_iva) if c.tna_c_iva is not None else 0.0,
            "Plazo": c.plazo if c.plazo is not None else 0,
            "Fecha Emisión": c.fecha_emision.strftime("%Y-%m-%d") if hasattr(c.fecha_emision, 'strftime') else str(c.fecha_emision),
            "Estado": c.estado.value if hasattr(c.estado, 'value') else str(c.estado) if c.estado else "-",
            "Tipo Crédito": c.tipo_credito.value if hasattr(c.tipo_credito, 'value') else str(c.tipo_credito) if c.tipo_credito else "-",
            "Día Vto": c.dia_vencimiento,
            "Saldo en Mora": float(round(saldo_mora, 2)),
            "Días de Mora": dias_mora
        })
    return result

@router.delete("/api/v1/creditos/{credito_id:int}")
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
@router.post("/api/v1/creditos/{credito_id:int}/documentos", response_model=DocumentoLegajoOut)
async def upload_documento(credito_id: int, file: UploadFile = File(...), transferencia_id: Optional[int] = Form(None), es_legajo_firmado: bool = Form(False), db: Session = Depends(get_db)):
    try:
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
        
        if es_legajo_firmado and credito.estado in (EstadoCredito.APROBADO, "APROBADO", "EstadoCredito.APROBADO"):
            credito.estado = EstadoCredito.FIRMADO.value

        db.commit()
        db.refresh(nuevo_doc)

        if credito.estado in (EstadoCredito.APROBADO, EstadoCredito.FIRMADO, "APROBADO", "FIRMADO", "EstadoCredito.APROBADO", "EstadoCredito.FIRMADO"):
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
    except Exception as e:
        import traceback
        error_msg = f"Error interno: {str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/api/v1/creditos/{credito_id:int}/documentos", response_model=List[DocumentoLegajoOut])
def get_documentos(credito_id: int, db: Session = Depends(get_db)):
    docs = db.query(DocumentoLegajo).filter(DocumentoLegajo.credito_id == credito_id).all()
    return docs

@router.delete("/api/v1/creditos/{credito_id:int}/documentos/{doc_id:int}")
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

@router.get("/api/v1/creditos/{credito_id:int}/documentos/merged/download")
def download_merged_pdf(credito_id: int, db: Session = Depends(get_db)):
    docs = db.query(DocumentoLegajo).filter(DocumentoLegajo.credito_id == credito_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail="No hay documentos para este crédito")

    # Ordenar: Documentos generales primero (transferencia_id is None), transferencias al final
    docs = sorted(docs, key=lambda d: 1 if d.transferencia_id is not None else 0)

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

@router.get("/api/v1/creditos/{credito_id:int}/documentos/{doc_id:int}/download")
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
            if credito.estado in (EstadoCredito.APROBADO, EstadoCredito.FIRMADO, "APROBADO", "FIRMADO", "EstadoCredito.APROBADO", "EstadoCredito.FIRMADO"):
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


import pandas as pd
import base64
import tempfile
import importlib
import traceback
from src.logic.import_data import quota

@router.post("/api/v1/creditos/importacion-masiva")
async def importacion_masiva_creditos(
    proveedor: str = Form("QUOTA_CFL"),
    clientes_file: UploadFile = File(...),
    creditos_file: UploadFile = File(...),
    transferencias_file: UploadFile = File(...),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    if proveedor != "QUOTA_CFL":
        raise HTTPException(status_code=400, detail="Proveedor no soportado actualmente.")

    try:
        # 1. Leer Archivos en Memoria
        clts_bytes = await clientes_file.read()
        df_clts = pd.read_excel(BytesIO(clts_bytes))
        df_clts.columns = [str(c).strip() for c in df_clts.columns]
        
        crts_bytes = await creditos_file.read()
        df_crts = pd.read_excel(BytesIO(crts_bytes))
        df_crts.columns = [str(c).strip() for c in df_crts.columns]

        # Normalizar variaciones de nombres de columnas frecuentes
        col_mappings = {
            'Credito': 'Crédito',
            'id externo': 'ID Externo',
            'id_externo': 'ID Externo',
            'ID EXTERNO': 'ID Externo',
            'Imp.Cuota': 'Imp. Cuota',
            'Imp Cuota': 'Imp. Cuota',
            'Emision': 'Emisión',
        }
        df_crts.rename(columns=col_mappings, inplace=True)
        
        transf_bytes = await transferencias_file.read()
        try:
            df_transf = pd.read_csv(BytesIO(transf_bytes), sep=";", header=None, names=["CBU/CVU", "Fecha", "Monto", "CUIT/CUIL", "ID Quota", "Razon Social"], encoding="utf-8")
        except Exception:
            df_transf = pd.read_csv(BytesIO(transf_bytes), sep=";", header=None, names=["CBU/CVU", "Fecha", "Monto", "CUIT/CUIL", "ID Quota", "Razon Social"], encoding="latin-1", on_bad_lines='skip')

        # 2. Pipeline de Importación Quota
        errores_globales = []
        
        res_clts = quota.import_clients_from_dataframe(df_clts, db)
        if res_clts.get('errores'):
            errores_globales.extend([{"Etapa": "Clientes", "Error": err} for err in res_clts['errores']])
            
        res_crts_upd = quota.update_clients_from_crts_dataframe(df_crts, db)
        if res_crts_upd.get('errores'):
            errores_globales.extend([{"Etapa": "Actualización Clientes", "Error": err} for err in res_crts_upd['errores']])
            
        res_crts = quota.import_credits_from_dataframe(df_crts, db)
        if res_crts.get('errores'):
            errores_globales.extend([{"Etapa": "Créditos", "Error": err} for err in res_crts['errores']])
            
        nuevos_ids = res_crts.get('nuevos_ids_externos', set())
        
        res_transf = quota.import_transfers_from_dataframe(df_transf, df_crts, db, nuevos_ids_externos=nuevos_ids)
        if res_transf.get('errores'):
            errores_globales.extend([{"Etapa": "Transferencias", "Error": err} for err in res_transf['errores']])

        # 3. Procesar Archivos (Legajos)
        archivos_procesados = 0
        if archivos:
            with tempfile.TemporaryDirectory() as tmpdirname:
                extracted_files = []
                for file in archivos:
                    if file.filename.lower().endswith(".zip"):
                        content = await file.read()
                        with zipfile.ZipFile(BytesIO(content)) as zf:
                            for zip_info in zf.infolist():
                                if not zip_info.is_dir() and not zip_info.filename.startswith("__MACOSX/") and not zip_info.filename.startswith("."):
                                    extracted_bytes = zf.read(zip_info.filename)
                                    base_name = os.path.basename(zip_info.filename)
                                    if base_name:
                                        file_path = os.path.join(tmpdirname, base_name)
                                        with open(file_path, "wb") as f:
                                            f.write(extracted_bytes)
                                        extracted_files.append(file_path)
                    else:
                        file_bytes = await file.read()
                        file_path = os.path.join(tmpdirname, file.filename)
                        with open(file_path, "wb") as f:
                            f.write(file_bytes)
                        extracted_files.append(file_path)

                if extracted_files:
                    res_docs = quota.process_quota_documents(
                        file_paths=extracted_files,
                        df_crts=df_crts,
                        session=db,
                        upload_dir=UPLOAD_DIR,
                        nuevos_ids_externos=nuevos_ids
                    )
                    archivos_procesados = len(res_docs.get('procesados', []))
                    if res_docs.get('errores'):
                        errores_globales.extend([{"Etapa": "Documentos", "Error": str(err)} for err in res_docs['errores']])

        # 4. Verificar estados
        res_estados = quota.verify_and_update_credit_states(df_crts, db)
        if res_estados.get('errores'):
            errores_globales.extend([{"Etapa": "Verificación Estados", "Error": err} for err in res_estados['errores']])

        # 5. Generar reporte de errores si los hay
        excel_base64 = None
        if errores_globales:
            df_err = pd.DataFrame(errores_globales)
            out_stream = BytesIO()
            with pd.ExcelWriter(out_stream, engine='openpyxl') as writer:
                df_err.to_excel(writer, index=False, sheet_name='Errores')
            excel_base64 = base64.b64encode(out_stream.getvalue()).decode('utf-8')

        return {
            "status": "success",
            "message": "Importación procesada",
            "resumen": {
                "nuevos_clientes": res_clts.get('nuevos', 0),
                "clientes_actualizados": res_clts.get('actualizados', 0) + res_crts_upd.get('actualizados', 0),
                "nuevos_creditos": res_crts.get('nuevos_creditos', 0),
                "creditos_existentes": res_crts.get('creditos_existentes', 0),
                "transferencias_importadas": res_transf.get('importadas', 0),
                "archivos_procesados": archivos_procesados,
                "pasados_a_firmado": res_estados.get('pasados_a_firmado', 0),
                "pasados_a_activo": res_estados.get('pasados_a_activo', 0)
            },
            "errores_count": len(errores_globales),
            "excel_base64": excel_base64
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error durante importación masiva: {str(e)}\n{traceback.format_exc()}")
