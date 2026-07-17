from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.database.models.cobranzas import Cobranza
from src.database.models.facturacion import Factura
from src.logic.facturacion import procesar_facturacion_pendiente
import pandas as pd
import io
import zipfile
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

router = APIRouter(prefix="/api/v1/facturacion", tags=["Facturación"])

@router.get("/pendientes")
def get_pendientes(db: Session = Depends(get_db)):
    cobranzas = db.query(Cobranza).filter(Cobranza.facturada == False).all()
    res = []
    for c in cobranzas:
        res.append({
            "id": c.id,
            "cuota_id": c.cuota_id,
            "fecha": str(c.fecha),
            "capital": float(c.capital),
            "interes": float(c.interes),
            "iva": float(c.iva),
            "importe_total": float(c.importe_total),
            "tipo_cobranza": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, 'value') else str(c.tipo_cobranza)
        })
    return res

@router.post("/procesar")
def procesar_facturacion(db: Session = Depends(get_db)):
    cantidad = procesar_facturacion_pendiente(db)
    return {"message": f"Se procesaron {cantidad} facturas."}

@router.get("/libro-iva")
def descargar_libro_iva(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Factura)
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    facturas = query.all()
    
    data = []
    for f in facturas:
        data.append({
            "Fecha": f.fecha_emision.strftime("%d/%m/%Y"),
            "Tipo Comprobante": "Factura B" if f.tipo_comprobante == 6 else f"Comprobante {f.tipo_comprobante}",
            "Punto Venta": f.punto_venta,
            "Nro Comprobante": f.nro_comprobante,
            "CUIT Cliente": f.cuit_cliente or "Consumidor Final",
            "Importe Total": float(f.importe_total),
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
    query = db.query(Factura)
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    facturas = query.all()
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for f in facturas:
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(2*cm, 27*cm, f"FACTURA {'B' if f.tipo_comprobante == 6 else 'C'}")
            c.setFont("Helvetica", 12)
            c.drawString(2*cm, 26*cm, f"Nro: {f.punto_venta:04d}-{f.nro_comprobante:08d}")
            c.drawString(2*cm, 25*cm, f"Fecha: {f.fecha_emision.strftime('%d/%m/%Y')}")
            c.drawString(2*cm, 24*cm, f"CUIT Cliente: {f.cuit_cliente or 'Consumidor Final'}")
            
            c.drawString(2*cm, 22*cm, "Detalle:")
            c.drawString(2*cm, 21*cm, f"Cobranza ID: {f.cobranza_id}")
            c.drawString(2*cm, 20*cm, f"Importe Total: $ {float(f.importe_total):.2f}")
            
            c.drawString(2*cm, 18*cm, f"CAE: {f.cae}")
            if f.vencimiento_cae:
                c.drawString(2*cm, 17.5*cm, f"Vto CAE: {f.vencimiento_cae.strftime('%d/%m/%Y')}")
            
            c.showPage()
            c.save()
            
            pdf_buffer.seek(0)
            filename = f"Factura_{f.punto_venta:04d}_{f.nro_comprobante:08d}.pdf"
            zip_file.writestr(filename, pdf_buffer.getvalue())
            
    zip_buffer.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="facturas.zip"'
    }
    return StreamingResponse(iter([zip_buffer.getvalue()]), media_type="application/zip", headers=headers)
