from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from src.database import get_db
from src.database.models.cobranzas import Cobranza
from src.database.models.facturacion import Factura
from src.database.models.creditos import Cuota, Credito
from src.logic.creditos.facturacion import procesar_facturacion_pendiente
import pandas as pd
import io
import zipfile
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from src.config import COMPANY_DATA

router = APIRouter(prefix="/api/v1/facturacion", tags=["Facturación"])

@router.get("/pendientes")
def get_pendientes(
    skip: int = 0,
    limit: int = 1000,
    socios: Optional[str] = None,
    fecha_emision_desde: Optional[str] = None,
    fecha_emision_hasta: Optional[str] = None,
    fecha_vto_desde: Optional[str] = None,
    fecha_vto_hasta: Optional[str] = None,
    procesos: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Cobranza).options(
        joinedload(Cobranza.cuota).joinedload(Cuota.credito).joinedload(Credito.socio_originador),
        joinedload(Cobranza.proceso)
    ).filter(Cobranza.facturada == False)
    
    if fecha_emision_desde:
        query = query.filter(Cobranza.fecha >= fecha_emision_desde)
    if fecha_emision_hasta:
        query = query.filter(Cobranza.fecha <= fecha_emision_hasta)

    # Some filters need to be applied in python or with joins
    cobranzas = query.order_by(Cobranza.id.desc()).all()
    
    res = []
    for c in cobranzas:
        socio_nombre = "N/A"
        if c.cuota and c.cuota.credito and c.cuota.credito.socio_originador:
            socio_nombre = c.cuota.credito.socio_originador.razon_social
            
        if socios:
            socio_list = socios.split(',')
            if socio_nombre not in socio_list:
                continue

        vencimiento_cuota = str(c.cuota.fecha_vencimiento) if c.cuota and c.cuota.fecha_vencimiento else ""
        if fecha_vto_desde and vencimiento_cuota < fecha_vto_desde:
            continue
        if fecha_vto_hasta and vencimiento_cuota and vencimiento_cuota > fecha_vto_hasta:
            continue

        proceso_nombre = f"Lote #{c.proceso.id} - {c.proceso.tipo.value if hasattr(c.proceso.tipo, 'value') else c.proceso.tipo}" if c.proceso else "Sin Proceso"
        if procesos:
            procesos_list = procesos.split(',')
            if proceso_nombre not in procesos_list:
                continue
                
        res.append({
            "id": c.id,
            "cuota_id": c.cuota_id,
            "fecha": str(c.fecha),
            "capital": float(c.capital),
            "interes": float(c.interes),
            "iva": float(c.iva),
            "importe_total": float(c.importe_total),
            "tipo_cobranza": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, 'value') else str(c.tipo_cobranza),
            "socio_originador": socio_nombre,
            "vencimiento_cuota": vencimiento_cuota or None,
            "proceso_id": c.proceso_id,
            "proceso_nombre": proceso_nombre
        })
        
    total = len(res)
    items = res[skip : skip + limit]
    return {"items": items, "total": total}

@router.get("/ultima-fecha")
def get_ultima_fecha_factura(db: Session = Depends(get_db)):
    ultima = db.query(Factura).order_by(Factura.fecha_emision.desc(), Factura.id.desc()).first()
    return {"ultima_fecha": str(ultima.fecha_emision) if ultima else None}

class ProcesarRequest(BaseModel):
    cobranza_ids: Optional[List[int]] = None
    fecha_emision: Optional[date] = None

@router.post("/procesar")
def procesar_facturacion(request: ProcesarRequest, db: Session = Depends(get_db)):
    cantidad = procesar_facturacion_pendiente(db, cobranza_ids=request.cobranza_ids, fecha_emision=request.fecha_emision)
    return {"message": f"Se procesaron {cantidad} facturas."}

@router.get("/libro-iva")
def descargar_libro_iva(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Factura).options(
        joinedload(Factura.cobranza).joinedload(Cobranza.cuota).joinedload(Cuota.credito).joinedload(Credito.socio_originador)
    )
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    facturas = query.all()
    
    data = []
    for f in facturas:
        cobranza = f.cobranza
        cuota = cobranza.cuota if cobranza else None
        credito = cuota.credito if cuota else None
        socio = credito.socio_originador if credito else None
        
        socio_nombre = socio.razon_social if socio else "N/A"
        nro_credito = credito.id if credito else "N/A"
        nro_cuota = cuota.nro_cuota if cuota else "N/A"
        
        capital = float(cobranza.capital) if cobranza else 0.0
        interes = float(cobranza.interes) if cobranza else 0.0
        iva = float(cobranza.iva) if cobranza else 0.0

        data.append({
            "Fecha": f.fecha_emision.strftime("%d/%m/%Y"),
            "Tipo Comprobante": "Factura B" if f.tipo_comprobante == 6 else f"Comprobante {f.tipo_comprobante}",
            "Punto Venta": f.punto_venta,
            "Nro Comprobante": f.nro_comprobante,
            "CUIT Cliente": f.cuit_cliente or "Consumidor Final",
            "NO GRAVADO": capital,
            "GRAVADO": interes,
            "IVA": iva,
            "Importe Total": float(f.importe_total),
            "Socio Originador": socio_nombre,
            "Nro Crédito": nro_credito,
            "Nro Cuota": nro_cuota,
            "CAE": f.cae,
            "Vto CAE": f.vencimiento_cae.strftime("%d/%m/%Y") if f.vencimiento_cae else ""
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Libro IVA Ventas")
    
    output.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="libro_iva_ventas.xlsx"'
    }
    return Response(content=output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

@router.get("/descargar-masivo")
def descargar_pdfs_masivo(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db)
):
    from src.config import get_company_data
    import os
    
    company_data_db = get_company_data(db)
    
    query = db.query(Factura).options(
        joinedload(Factura.cobranza).joinedload(Cobranza.cuota).joinedload(Cuota.credito)
    )
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    facturas = query.all()
    
    def format_currency(val):
        s = f"{float(val):,.2f}"
        return "$ " + s.replace(',', 'X').replace('.', ',').replace('X', '.')
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for f in facturas:
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            # A4 is 21cm x 29.7cm
            width, height = A4
            
            # Draw outer border
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.rect(1*cm, 1*cm, width - 2*cm, height - 2*cm)
            
            # Header line
            c.line(1*cm, height - 5*cm, width - 1*cm, height - 5*cm)
            
            # Logo
            logo_path = os.path.join("data", "uploads", "logo.png")
            if os.path.exists(logo_path):
                c.drawImage(logo_path, 1.5*cm, height - 4.8*cm, width=7.5*cm, height=3.5*cm, preserveAspectRatio=True, anchor='nw')
            else:
                # Logo Placeholder
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.rect(1.5*cm, height - 4.8*cm, 7.5*cm, 3.5*cm)
                c.setFont("Helvetica", 9)
                c.setFillColorRGB(0.6, 0.6, 0.6)
                c.drawCentredString(5.25*cm, height - 3.2*cm, "[ESPACIO LOGO]")
            
            # Letter (B or C) box
            c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(1, 1, 1)
            c.rect(width/2 - 0.8*cm, height - 2.5*cm, 1.6*cm, 1.6*cm, stroke=1, fill=1)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 24)
            letra_comp = 'B' if f.tipo_comprobante == 6 else 'C'
            c.drawCentredString(width/2, height - 2.0*cm, letra_comp)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(width/2, height - 2.8*cm, f"Cod. {f.tipo_comprobante:03d}")
            
            # Factura title
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(width/2 + 1.5*cm, height - 2*cm, "FACTURA")
            
            # Factura Details (Header Right)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(width/2 + 1.5*cm, height - 2.7*cm, f"Comp. Nro: {f.punto_venta:04d}-{f.nro_comprobante:08d}")
            c.drawString(width/2 + 1.5*cm, height - 3.3*cm, f"Fecha de Emisión: {f.fecha_emision.strftime('%d/%m/%Y')}")
            
            # Company Details (Header Left, below logo)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1.5*cm, height - 5.5*cm, f"Razón Social: {company_data_db.razon_social}")
            c.setFont("Helvetica", 9)
            c.drawString(1.5*cm, height - 6.0*cm, f"Domicilio Comercial: {company_data_db.domicilio}")
            c.drawString(1.5*cm, height - 6.5*cm, "Condición frente al IVA: Responsable Inscripto")
            
            # Additional company details
            c.setFont("Helvetica-Bold", 10)
            c_cuit = company_data_db.cuit
            cuit_formateado = f"{c_cuit[:2]}-{c_cuit[2:10]}-{c_cuit[10:]}" if len(c_cuit) == 11 else c_cuit
            c.drawString(11*cm, height - 5.5*cm, f"CUIT: {cuit_formateado}")
            c.setFont("Helvetica", 9)
            c.drawString(11*cm, height - 6.0*cm, f"Ingresos Brutos: {c_cuit}")
            c.drawString(11*cm, height - 6.5*cm, "Fecha de Inicio de Actividades: 01/01/2020")
            
            # Client details section
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.line(1*cm, height - 7*cm, width - 1*cm, height - 7*cm)
            
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(1.5*cm, height - 7.6*cm, "CUIT/CUIL:")
            c.setFont("Helvetica", 9)
            c.drawString(7.5*cm, height - 7.6*cm, f"{f.cuit_cliente or 'Consumidor Final'}")
            
            cliente_nombre = "Consumidor Final"
            cliente_domicilio = "N/A"
            if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito and f.cobranza.cuota.credito.cliente:
                cliente = f.cobranza.cuota.credito.cliente
                cliente_nombre = f"{cliente.apellido}, {cliente.nombre}"
                if cliente.calle:
                    cliente_domicilio = f"{cliente.calle} {cliente.calle_nro or ''}, {cliente.localidad or ''}"
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(1.5*cm, height - 8.2*cm, "Apellido y Nombre / Razón Social:")
            c.setFont("Helvetica", 9)
            c.drawString(7.5*cm, height - 8.2*cm, cliente_nombre)
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(1.5*cm, height - 8.8*cm, "Domicilio Comercial:")
            c.setFont("Helvetica", 9)
            c.drawString(7.5*cm, height - 8.8*cm, cliente_domicilio)
            
            # Line separator
            c.line(1*cm, height - 9.4*cm, width - 1*cm, height - 9.4*cm)
            
            # Detail table headers
            c.setFillColorRGB(0.9, 0.9, 0.9)
            c.rect(1*cm, height - 10.2*cm, width - 2*cm, 0.8*cm, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1.5*cm, height - 9.9*cm, "Descripción")
            c.drawRightString(width - 1.5*cm, height - 9.9*cm, "Importe Total")
            c.line(1*cm, height - 10.2*cm, width - 1*cm, height - 10.2*cm)
            
            # Detail rows
            c.setFont("Helvetica", 10)
            
            y_pos = height - 10.8*cm
            
            es_penalty = False
            if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito:
                credito = f.cobranza.cuota.credito
                c_tipo = getattr(credito.tipo_credito, 'value', str(credito.tipo_credito))
                if "PENALTY" in c_tipo:
                    es_penalty = True

            if f.cobranza:
                if f.cobranza.capital and f.cobranza.capital > 0:
                    label_capital = "Penalty" if es_penalty else "Capital"
                    c.drawString(1.5*cm, y_pos, label_capital)
                    c.drawRightString(width - 1.5*cm, y_pos, format_currency(f.cobranza.capital))
                    y_pos -= 0.6*cm
                
                # Para Factura B (tipo 6) o C (tipo 11), el IVA suele ir incluido
                # Sumamos interés + iva
                monto_interes = float(f.cobranza.interes or 0)
                monto_iva = float(getattr(f.cobranza, 'iva', 0) or 0)
                monto_total_interes = monto_interes + monto_iva
                
                if monto_total_interes > 0:
                    label_interes = "Penalty" if es_penalty else "Interés"
                    c.drawString(1.5*cm, y_pos, label_interes)
                    c.drawRightString(width - 1.5*cm, y_pos, format_currency(monto_total_interes))
                    y_pos -= 0.6*cm
            else:
                descripcion = f"Cancelación de Cuota - Cobranza ID: {f.cobranza_id}"
                c.drawString(1.5*cm, y_pos, descripcion)
                c.drawRightString(width - 1.5*cm, y_pos, format_currency(f.importe_total))
            
            # Totals
            c.line(1*cm, 5*cm, width - 1*cm, 5*cm)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(width - 7*cm, 4*cm, "Total:")
            c.drawRightString(width - 1.5*cm, 4*cm, format_currency(f.importe_total))
            
            # Observaciones
            if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(1.5*cm, 3.2*cm, "Observaciones:")
                c.setFont("Helvetica", 10)
                obs = f"Cancelación de Cuota {f.cobranza.cuota.nro_cuota} correspondiente al Crédito Nro. {f.cobranza.cuota.credito.id}"
                c.drawString(4.5*cm, 3.2*cm, obs)
            
            # Footer (CAE)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1.5*cm, 2.5*cm, f"CAE Nro:")
            c.setFont("Helvetica", 10)
            c.drawString(3.5*cm, 2.5*cm, f"{f.cae}")
            
            if f.vencimiento_cae:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(1.5*cm, 2*cm, f"Fecha Vto. CAE:")
                c.setFont("Helvetica", 10)
                c.drawString(4.5*cm, 2*cm, f"{f.vencimiento_cae.strftime('%d/%m/%Y')}")
            
            c.showPage()
            c.save()
            
            pdf_buffer.seek(0)
            
            nro_credito_str = ""
            if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito:
                nro_credito_str = f"_Credito_{f.cobranza.cuota.credito.id}"
                
            c_cuil_str = f"_CUIL_{f.cuit_cliente}" if f.cuit_cliente else ""
            
            filename = f"Factura_{f.punto_venta:04d}_{f.nro_comprobante:08d}{nro_credito_str}{c_cuil_str}.pdf"
            zip_file.writestr(filename, pdf_buffer.getvalue())
            
    zip_buffer.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="facturas.zip"'
    }
    return StreamingResponse(iter([zip_buffer.getvalue()]), media_type="application/zip", headers=headers)
