from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from sqlalchemy.orm import Session, joinedload
from datetime import date
import pandas as pd
import io
import os
import re
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from src.database import get_db
from src.database.models.creditos.cobranzas import Cobranza
from src.database.models.creditos.facturacion import (
    Factura,
    TIPOS_COMPROBANTE_ARCA,
    TIPOS_COMPROBANTE_MAP,
    CODIGOS_NOTA_CREDITO,
    CODIGOS_NOTA_DEBITO,
    CODIGOS_FCE_MIPYME,
    get_info_tipo_comprobante,
)
from src.database.models.creditos.creditos import Cuota, Credito
from src.database.models.creditos.clientes import Cliente, Provincia
from src.database.models.socios import SocioComercial
from src.database.models.finance.comprobantes import Proveedor
from src.database.models.deuda.inversores import Inversor
from src.logic.creditos.facturacion import procesar_facturacion_pendiente
from src.services.arca_service import ArcaService
from src.config import get_company_data

router = APIRouter(prefix="/api/v1/facturacion", tags=["Facturación"])


def _extract_factura_breakdown(f: Factura) -> dict[str, float]:
    """
    Obtiene el desglose impositivo de una Factura.
    Si es una factura histórica de cobranza sin desglose propio cargado en las nuevas
    columnas, toma capital/interés/iva de la Cobranza vinculada.
    """
    no_gravado = float(f.importe_no_gravado or 0.0)
    exento = float(f.importe_exento or 0.0)
    neto_21 = float(f.neto_gravado_21 or 0.0)
    neto_105 = float(f.neto_gravado_105 or 0.0)
    neto_27 = float(f.neto_gravado_27 or 0.0)
    iva_21 = float(f.iva_21 or 0.0)
    iva_105 = float(f.iva_105 or 0.0)
    iva_27 = float(f.iva_27 or 0.0)
    perc_iva = float(f.percepcion_iva or 0.0)
    perc_iibb = float(f.percepcion_iibb or 0.0)
    otros_imp = float(f.otros_impuestos or 0.0)

    own_sum = (
        no_gravado + exento + neto_21 + neto_105 + neto_27
        + iva_21 + iva_105 + iva_27 + perc_iva + perc_iibb + otros_imp
    )
    if own_sum == 0.0 and f.cobranza is not None:
        no_gravado = float(f.cobranza.capital or 0.0)
        neto_21 = float(f.cobranza.interes or 0.0)
        iva_21 = float(f.cobranza.iva or 0.0)

    neto_gravado_total = round(neto_21 + neto_105 + neto_27, 2)
    iva_total = round(iva_21 + iva_105 + iva_27, 2)
    otros_tributos_total = round(perc_iva + perc_iibb + otros_imp, 2)
    importe_total = round(float(f.importe_total or 0.0), 2)

    return {
        "importe_no_gravado": round(no_gravado, 2),
        "importe_exento": round(exento, 2),
        "neto_gravado_21": round(neto_21, 2),
        "neto_gravado_105": round(neto_105, 2),
        "neto_gravado_27": round(neto_27, 2),
        "neto_gravado_total": neto_gravado_total,
        "iva_21": round(iva_21, 2),
        "iva_105": round(iva_105, 2),
        "iva_27": round(iva_27, 2),
        "iva_total": iva_total,
        "percepcion_iva": round(perc_iva, 2),
        "percepcion_iibb": round(perc_iibb, 2),
        "otros_impuestos": round(otros_imp, 2),
        "otros_tributos_total": otros_tributos_total,
        "importe_total": importe_total,
    }


def _format_currency_ar(val: float) -> str:
    s = f"{float(val or 0.0):,.2f}"
    return "$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def generar_factura_pdf_bytes(f: Factura, company_data_db) -> bytes:
    """
    Genera el PDF reglamentario A4 para cualquier comprobante ARCA (Factura A/B/C/M/E,
    Nota de Crédito/Débito, Recibo o FCE MiPyME).
    """
    info_tipo = get_info_tipo_comprobante(f.tipo_comprobante)
    breakdown = _extract_factura_breakdown(f)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # Borde exterior
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.rect(1 * cm, 1 * cm, width - 2 * cm, height - 2 * cm)

    # Línea cabecera
    c.line(1 * cm, height - 5 * cm, width - 1 * cm, height - 5 * cm)

    # Logo institucional (data/public/logo.png o data/uploads/logo.png)
    logo_candidates = [
        os.path.join("data", "public", "logo.png"),
        os.path.join("data", "uploads", "logo.png"),
    ]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
    if logo_path:
        c.drawImage(
            logo_path,
            1.5 * cm,
            height - 4.8 * cm,
            width=7.5 * cm,
            height=3.5 * cm,
            preserveAspectRatio=True,
            anchor="nw",
        )
    else:
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.rect(1.5 * cm, height - 4.8 * cm, 7.5 * cm, 3.5 * cm)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(5.25 * cm, height - 3.2 * cm, company_data_db.razon_social[:28])

    # Recuadro central con Letra (A, B, C, M, E) y Código ARCA
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(1, 1, 1)
    c.rect(width / 2 - 0.8 * cm, height - 2.5 * cm, 1.6 * cm, 1.6 * cm, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 2.0 * cm, info_tipo["letra"])
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width / 2, height - 2.8 * cm, f"Cod. {int(f.tipo_comprobante):03d}")

    # Título del Comprobante (FACTURA, NOTA DE CRÉDITO, NOTA DE DÉBITO, etc.)
    c.setFillColorRGB(0, 0, 0)
    titulo = info_tipo["titulo"]
    c.setFont("Helvetica-Bold", 14 if len(titulo) > 14 else 18)
    c.drawString(width / 2 + 1.3 * cm, height - 2.0 * cm, titulo)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(
        width / 2 + 1.3 * cm,
        height - 2.7 * cm,
        f"Comp. Nro: {int(f.punto_venta):04d}-{int(f.nro_comprobante):08d}",
    )
    c.drawString(
        width / 2 + 1.3 * cm,
        height - 3.3 * cm,
        f"Fecha de Emisión: {f.fecha_emision.strftime('%d/%m/%Y')}",
    )

    if f.comprobante_asociado_str:
        c.setFont("Helvetica", 8.5)
        c.drawString(
            width / 2 + 1.3 * cm,
            height - 3.9 * cm,
            f"Comp. Asociado: {f.comprobante_asociado_str[:38]}",
        )

    # Datos de la Empresa Emisora
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, height - 5.5 * cm, f"Razón Social: {company_data_db.razon_social}")
    c.setFont("Helvetica", 9)
    c.drawString(1.5 * cm, height - 6.0 * cm, f"Domicilio Comercial: {company_data_db.domicilio}")
    c.drawString(1.5 * cm, height - 6.5 * cm, "Condición frente al IVA: Responsable Inscripto")

    c.setFont("Helvetica-Bold", 10)
    c_cuit = str(company_data_db.cuit or "")
    cuit_formateado = f"{c_cuit[:2]}-{c_cuit[2:10]}-{c_cuit[10:]}" if len(c_cuit) == 11 else c_cuit
    c.drawString(11 * cm, height - 5.5 * cm, f"CUIT: {cuit_formateado}")
    c.setFont("Helvetica", 9)
    c.drawString(11 * cm, height - 6.0 * cm, f"Ingresos Brutos: {c_cuit}")
    c.drawString(11 * cm, height - 6.5 * cm, "Fecha de Inicio de Actividades: 01/01/2020")

    # Sección de datos del Receptor
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(1 * cm, height - 7.0 * cm, width - 1 * cm, height - 7.0 * cm)

    cliente_nombre = f.razon_social_receptor or "Consumidor Final"
    cliente_domicilio = f.domicilio_receptor or "N/A"
    condicion_iva = f.condicion_iva_receptor or (
        "Responsable Inscripto" if info_tipo["letra"] in ("A", "M") else "Consumidor Final"
    )
    if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito and f.cobranza.cuota.credito.cliente:
        cli = f.cobranza.cuota.credito.cliente
        if not f.razon_social_receptor:
            cliente_nombre = f"{cli.apellido}, {cli.nombre}"
        if not f.domicilio_receptor and cli.calle:
            cliente_domicilio = f"{cli.calle} {cli.calle_nro or ''}, {cli.localidad or ''}"

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1.5 * cm, height - 7.6 * cm, f"{f.tipo_doc_receptor or 'CUIT/CUIL'}:")
    c.setFont("Helvetica", 9)
    c.drawString(4.5 * cm, height - 7.6 * cm, f"{f.cuit_cliente or 'Consumidor Final'}")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(10.5 * cm, height - 7.6 * cm, "Condición IVA:")
    c.setFont("Helvetica", 9)
    c.drawString(13.3 * cm, height - 7.6 * cm, condicion_iva[:32])

    c.setFont("Helvetica-Bold", 9)
    c.drawString(1.5 * cm, height - 8.2 * cm, "Apellido y Nombre / Razón Social:")
    c.setFont("Helvetica", 9)
    c.drawString(7.2 * cm, height - 8.2 * cm, cliente_nombre[:60])

    c.setFont("Helvetica-Bold", 9)
    c.drawString(1.5 * cm, height - 8.8 * cm, "Domicilio Comercial:")
    c.setFont("Helvetica", 9)
    c.drawString(7.2 * cm, height - 8.8 * cm, cliente_domicilio[:65])

    c.line(1 * cm, height - 9.4 * cm, width - 1 * cm, height - 9.4 * cm)

    # Encabezado de tabla de conceptos/ítems
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(1 * cm, height - 10.2 * cm, width - 2 * cm, 0.8 * cm, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(1.5 * cm, height - 9.9 * cm, "Descripción / Concepto")
    c.drawRightString(width - 7.5 * cm, height - 9.9 * cm, "Cant.")
    c.drawRightString(width - 4.5 * cm, height - 9.9 * cm, "P. Unit.")
    c.drawRightString(width - 1.5 * cm, height - 9.9 * cm, "Subtotal")
    c.line(1 * cm, height - 10.2 * cm, width - 1 * cm, height - 10.2 * cm)

    c.setFont("Helvetica", 9.5)
    y_pos = height - 10.8 * cm

    items = f.items_detalle if isinstance(f.items_detalle, list) and len(f.items_detalle) > 0 else None
    if items:
        for item in items[:15]:
            desc = str(item.get("descripcion") or "Concepto facturado")[:65]
            cant = float(item.get("cantidad") or 1)
            p_unit = float(item.get("precio_unitario") or 0.0)
            sub = float(item.get("subtotal") or (cant * p_unit))
            c.drawString(1.5 * cm, y_pos, desc)
            c.drawRightString(width - 7.5 * cm, y_pos, f"{cant:g}")
            c.drawRightString(width - 4.5 * cm, y_pos, _format_currency_ar(p_unit))
            c.drawRightString(width - 1.5 * cm, y_pos, _format_currency_ar(sub))
            y_pos -= 0.6 * cm
    elif f.cobranza:
        es_penalty = False
        if f.cobranza.cuota and f.cobranza.cuota.credito:
            credito = f.cobranza.cuota.credito
            c_tipo = getattr(credito.tipo_credito, "value", str(credito.tipo_credito))
            if "PENALTY" in c_tipo:
                es_penalty = True

        if f.cobranza.capital and float(f.cobranza.capital) > 0:
            label_capital = "Penalty" if es_penalty else "Capital"
            cap_val = float(f.cobranza.capital)
            c.drawString(1.5 * cm, y_pos, label_capital)
            c.drawRightString(width - 7.5 * cm, y_pos, "1")
            c.drawRightString(width - 4.5 * cm, y_pos, _format_currency_ar(cap_val))
            c.drawRightString(width - 1.5 * cm, y_pos, _format_currency_ar(cap_val))
            y_pos -= 0.6 * cm

        monto_interes = float(f.cobranza.interes or 0)
        monto_iva = float(getattr(f.cobranza, "iva", 0) or 0)
        monto_mostrar = monto_interes if info_tipo["discrimina_iva"] else (monto_interes + monto_iva)
        if monto_mostrar > 0:
            label_interes = "Penalty" if es_penalty else "Interés Financiero"
            c.drawString(1.5 * cm, y_pos, label_interes)
            c.drawRightString(width - 7.5 * cm, y_pos, "1")
            c.drawRightString(width - 4.5 * cm, y_pos, _format_currency_ar(monto_mostrar))
            c.drawRightString(width - 1.5 * cm, y_pos, _format_currency_ar(monto_mostrar))
            y_pos -= 0.6 * cm
    else:
        desc_default = f.observaciones or f"{info_tipo['nombre']} - Servicios Financieros"
        sub_base = (
            breakdown["neto_gravado_total"] + breakdown["importe_exento"] + breakdown["importe_no_gravado"]
            if info_tipo["discrimina_iva"]
            else breakdown["importe_total"]
        )
        c.drawString(1.5 * cm, y_pos, desc_default[:65])
        c.drawRightString(width - 7.5 * cm, y_pos, "1")
        c.drawRightString(width - 4.5 * cm, y_pos, _format_currency_ar(sub_base))
        c.drawRightString(width - 1.5 * cm, y_pos, _format_currency_ar(sub_base))
        y_pos -= 0.6 * cm

    # Pie de Subtotales e Impuestos Discriminados
    c.line(1 * cm, 7.2 * cm, width - 1 * cm, 7.2 * cm)
    if info_tipo["discrimina_iva"]:
        c.setFont("Helvetica", 9)
        y_tax = 6.6 * cm
        if breakdown["neto_gravado_total"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "Importe Neto Gravado:")
            c.drawRightString(width - 1.5 * cm, y_tax, _format_currency_ar(breakdown["neto_gravado_total"]))
            y_tax -= 0.42 * cm
        if breakdown["iva_21"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "IVA 21%:")
            c.drawRightString(width - 1.5 * cm, y_tax, _format_currency_ar(breakdown["iva_21"]))
            y_tax -= 0.42 * cm
        if breakdown["iva_105"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "IVA 10.5%:")
            c.drawRightString(width - 1.5 * cm, y_tax, _format_currency_ar(breakdown["iva_105"]))
            y_tax -= 0.42 * cm
        if breakdown["iva_27"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "IVA 27%:")
            c.drawRightString(width - 1.5 * cm, y_tax, _format_currency_ar(breakdown["iva_27"]))
            y_tax -= 0.42 * cm
        if breakdown["importe_exento"] + breakdown["importe_no_gravado"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "Exento / No Gravado:")
            c.drawRightString(
                width - 1.5 * cm,
                y_tax,
                _format_currency_ar(breakdown["importe_exento"] + breakdown["importe_no_gravado"]),
            )
            y_tax -= 0.42 * cm
        if breakdown["otros_tributos_total"] > 0:
            c.drawString(width - 8.5 * cm, y_tax, "Percepciones / Otros Tributos:")
            c.drawRightString(width - 1.5 * cm, y_tax, _format_currency_ar(breakdown["otros_tributos_total"]))

    c.setFont("Helvetica-Bold", 13)
    c.drawString(width - 8.5 * cm, 4.0 * cm, "Importe Total:")
    c.drawRightString(width - 1.5 * cm, 4.0 * cm, _format_currency_ar(breakdown["importe_total"]))

    # Observaciones
    obs_text = f.observaciones
    if not obs_text and f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito:
        obs_text = (
            f"Cancelación de Cuota {f.cobranza.cuota.nro_cuota} "
            f"correspondiente al Crédito Nro. {f.cobranza.cuota.credito.id}"
        )
    if obs_text:
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(1.5 * cm, 3.2 * cm, "Observaciones:")
        c.setFont("Helvetica", 9.5)
        c.drawString(4.3 * cm, 3.2 * cm, str(obs_text)[:85])

    # CAE y Vencimiento CAE
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, 2.3 * cm, "CAE Nro:")
    c.setFont("Helvetica", 10)
    c.drawString(3.5 * cm, 2.3 * cm, f"{f.cae or '-'}")

    if f.vencimiento_cae:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1.5 * cm, 1.8 * cm, "Fecha Vto. CAE:")
        c.setFont("Helvetica", 10)
        c.drawString(4.5 * cm, 1.8 * cm, f"{f.vencimiento_cae.strftime('%d/%m/%Y')}")

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


@router.get("/tipos-comprobante")
def get_tipos_comprobante():
    """Retorna el catálogo completo de tipos de comprobante electrónicos de ARCA."""
    return TIPOS_COMPROBANTE_ARCA


@router.get("/receptores")
def get_receptores_facturacion(db: Session = Depends(get_db)):
    """
    Retorna el directorio unificado de receptores registrados en el sistema
    (Socios Comerciales, Proveedores, Inversores y Clientes) junto con las Provincias,
    para autocompletar emisiones individuales de ARCA en Finanzas.
    """
    receptores: list[dict[str, Any]] = []

    socios = db.query(SocioComercial).order_by(SocioComercial.razon_social).all()
    for s in socios:
        receptores.append({
            "key": f"SOCIO:{s.id}",
            "tipo_entidad": "Socio Comercial",
            "tipo_doc": "CUIT",
            "nro_doc": s.cuit,
            "razon_social": s.razon_social,
            "domicilio": s.domicilio_legal or "",
            "provincia_id": None,
            "condicion_iva": "Responsable Inscripto",
        })

    proveedores = db.query(Proveedor).order_by(Proveedor.razon_social).all()
    for p in proveedores:
        cat_iva = p.categoria_impositiva.value if hasattr(p.categoria_impositiva, "value") else str(p.categoria_impositiva)
        t_doc = p.tipo_documento.value if hasattr(p.tipo_documento, "value") else "CUIT"
        receptores.append({
            "key": f"PROVEEDOR:{p.id}",
            "tipo_entidad": "Proveedor",
            "tipo_doc": t_doc,
            "nro_doc": p.nro_documento,
            "razon_social": p.razon_social,
            "domicilio": f"{p.domicilio or ''} {p.localidad or ''}".strip(),
            "provincia_id": p.provincia_id,
            "condicion_iva": cat_iva.title(),
        })

    inversores = db.query(Inversor).order_by(Inversor.razon_social).all()
    for inv in inversores:
        receptores.append({
            "key": f"INVERSOR:{inv.id}",
            "tipo_entidad": "Inversor",
            "tipo_doc": "CUIT",
            "nro_doc": inv.cuit,
            "razon_social": inv.razon_social,
            "domicilio": inv.domicilio_legal or "",
            "provincia_id": None,
            "condicion_iva": "Responsable Inscripto",
        })

    clientes = db.query(Cliente).order_by(Cliente.apellido, Cliente.nombre).limit(500).all()
    for cli in clientes:
        receptores.append({
            "key": f"CLIENTE:{cli.cuil}",
            "tipo_entidad": "Cliente",
            "tipo_doc": "CUIL",
            "nro_doc": cli.cuil,
            "razon_social": f"{cli.apellido}, {cli.nombre}",
            "domicilio": f"{cli.calle or ''} {cli.calle_nro or ''}, {cli.localidad or ''}".strip(", "),
            "provincia_id": cli.id_provincia,
            "condicion_iva": "Consumidor Final",
        })

    provincias = [
        {"id": pr.id, "nombre": pr.nombre}
        for pr in db.query(Provincia).order_by(Provincia.nombre).all()
    ]

    return {"receptores": receptores, "provincias": provincias}


class ItemFacturaInput(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=250)
    cantidad: float = Field(default=1.0, gt=0)
    precio_unitario: float = Field(..., ge=0)
    alicuota_iva: str = Field(default="21")  # "21", "10.5", "27", "0", "EXENTO", "NO_GRAVADO"


class EmitirFacturaIndividualRequest(BaseModel):
    punto_venta: int = Field(default=1, ge=1, le=99999)
    tipo_comprobante: int
    fecha_emision: Optional[date] = None
    concepto_arca: int = Field(default=2, ge=1, le=3)
    fecha_servicio_desde: Optional[date] = None
    fecha_servicio_hasta: Optional[date] = None
    fecha_vencimiento_pago: Optional[date] = None

    tipo_doc_receptor: str = Field(default="CUIT", max_length=15)
    cuit_cliente: Optional[str] = Field(default=None, max_length=20)
    razon_social_receptor: str = Field(default="Consumidor Final", max_length=200)
    domicilio_receptor: Optional[str] = Field(default=None, max_length=255)
    condicion_iva_receptor: str = Field(default="Consumidor Final", max_length=60)
    provincia_id: Optional[int] = None

    comprobante_asociado_id: Optional[int] = None
    comprobante_asociado_str: Optional[str] = Field(default=None, max_length=100)
    cbu_emisor: Optional[str] = Field(default=None, max_length=22)

    importe_no_gravado: float = Field(default=0.0, ge=0)
    importe_exento: float = Field(default=0.0, ge=0)
    neto_gravado_21: float = Field(default=0.0, ge=0)
    neto_gravado_105: float = Field(default=0.0, ge=0)
    neto_gravado_27: float = Field(default=0.0, ge=0)
    iva_21: Optional[float] = Field(default=None, ge=0)
    iva_105: Optional[float] = Field(default=None, ge=0)
    iva_27: Optional[float] = Field(default=None, ge=0)
    percepcion_iva: float = Field(default=0.0, ge=0)
    percepcion_iibb: float = Field(default=0.0, ge=0)
    otros_impuestos: float = Field(default=0.0, ge=0)
    importe_total: Optional[float] = Field(default=None, ge=0)

    items: Optional[List[ItemFacturaInput]] = None
    observaciones: Optional[str] = Field(default=None, max_length=500)


@router.post("/emitir-individual")
def emitir_factura_individual(
    payload: EmitirFacturaIndividualRequest,
    db: Session = Depends(get_db),
):
    """
    Emite un comprobante individual de ARCA desde el módulo de Finanzas
    (Facturas A, B, C, M, E, Notas de Crédito, Notas de Débito, Recibos y FCE MiPyME).
    """
    if payload.tipo_comprobante not in TIPOS_COMPROBANTE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de comprobante ARCA inválido ({payload.tipo_comprobante}).",
        )

    info_tipo = TIPOS_COMPROBANTE_MAP[payload.tipo_comprobante]
    cuit_clean = re.sub(r"\D", "", payload.cuit_cliente or "")

    if info_tipo["requiere_cuit"]:
        if info_tipo["letra"] == "E":
            if not (payload.cuit_cliente or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"{info_tipo['nombre']} requiere identificar el CUIT / ID Impositivo del receptor.",
                )
        elif len(cuit_clean) != 11:
            raise HTTPException(
                status_code=400,
                detail=f"{info_tipo['nombre']} requiere un CUIT válido de 11 dígitos para el receptor.",
            )

    comp_asoc_str = (payload.comprobante_asociado_str or "").strip() or None
    fact_asoc = None
    saldo_disponible_nc = None
    if payload.comprobante_asociado_id:
        fact_asoc = db.query(Factura).filter(Factura.id == payload.comprobante_asociado_id).first()
        if not fact_asoc:
            raise HTTPException(status_code=404, detail="El comprobante asociado indicado no existe.")
        if payload.tipo_comprobante in CODIGOS_NOTA_CREDITO and fact_asoc.tipo_comprobante in CODIGOS_NOTA_CREDITO:
            raise HTTPException(
                status_code=400,
                detail="No se puede emitir una Nota de Crédito sobre otra Nota de Crédito.",
            )
        info_asoc = get_info_tipo_comprobante(fact_asoc.tipo_comprobante)
        comp_asoc_str = f"{info_asoc['nombre']} {fact_asoc.punto_venta:04d}-{fact_asoc.nro_comprobante:08d}"

        if payload.tipo_comprobante in CODIGOS_NOTA_CREDITO:
            ncs_previas = (
                db.query(Factura)
                .filter(
                    Factura.comprobante_asociado_id == fact_asoc.id,
                    Factura.tipo_comprobante.in_(CODIGOS_NOTA_CREDITO),
                )
                .all()
            )
            ya_acreditado = round(sum(float(nc.importe_total or 0.0) for nc in ncs_previas), 2)
            saldo_disponible_nc = round(float(fact_asoc.importe_total or 0.0) - ya_acreditado, 2)
            if saldo_disponible_nc <= 0.01:
                raise HTTPException(
                    status_code=400,
                    detail="El comprobante asociado ya fue anulado en su totalidad mediante Nota(s) de Crédito.",
                )

    if (
        payload.tipo_comprobante in CODIGOS_NOTA_CREDITO
        or payload.tipo_comprobante in CODIGOS_NOTA_DEBITO
    ) and not comp_asoc_str:
        raise HTTPException(
            status_code=400,
            detail=f"Para emitir una {info_tipo['nombre']} es obligatorio indicar el comprobante asociado.",
        )

    no_gravado = round(float(payload.importe_no_gravado or 0.0), 2)
    exento = round(float(payload.importe_exento or 0.0), 2)
    neto_21 = round(float(payload.neto_gravado_21 or 0.0), 2)
    neto_105 = round(float(payload.neto_gravado_105 or 0.0), 2)
    neto_27 = round(float(payload.neto_gravado_27 or 0.0), 2)

    items_serializados: list[dict] = []
    has_explicit_netos = (no_gravado + exento + neto_21 + neto_105 + neto_27) > 0

    if payload.items:
        for it in payload.items:
            sub = round(float(it.cantidad) * float(it.precio_unitario), 2)
            alicuota = str(it.alicuota_iva).upper().strip()
            items_serializados.append({
                "descripcion": it.descripcion.strip(),
                "cantidad": float(it.cantidad),
                "precio_unitario": round(float(it.precio_unitario), 2),
                "alicuota_iva": alicuota,
                "subtotal": sub,
            })
            if not has_explicit_netos:
                if info_tipo["letra"] in ("C", "E") or alicuota in ("0", "EXENTO"):
                    exento = round(exento + sub, 2)
                elif alicuota == "NO_GRAVADO":
                    no_gravado = round(no_gravado + sub, 2)
                elif alicuota == "10.5":
                    if info_tipo["discrimina_iva"]:
                        neto_105 = round(neto_105 + sub, 2)
                    else:
                        neto_105 = round(neto_105 + (sub / 1.105), 2)
                elif alicuota == "27":
                    if info_tipo["discrimina_iva"]:
                        neto_27 = round(neto_27 + sub, 2)
                    else:
                        neto_27 = round(neto_27 + (sub / 1.27), 2)
                else:
                    if info_tipo["discrimina_iva"]:
                        neto_21 = round(neto_21 + sub, 2)
                    else:
                        neto_21 = round(neto_21 + (sub / 1.21), 2)

    if info_tipo["letra"] in ("C", "E"):
        iva_21 = 0.0
        iva_105 = 0.0
        iva_27 = 0.0
    else:
        iva_21 = round(float(payload.iva_21) if payload.iva_21 is not None else (neto_21 * 0.21), 2)
        iva_105 = round(float(payload.iva_105) if payload.iva_105 is not None else (neto_105 * 0.105), 2)
        iva_27 = round(float(payload.iva_27) if payload.iva_27 is not None else (neto_27 * 0.27), 2)

    perc_iva = round(float(payload.percepcion_iva or 0.0), 2)
    perc_iibb = round(float(payload.percepcion_iibb or 0.0), 2)
    otros_imp = round(float(payload.otros_impuestos or 0.0), 2)

    total_calculado = round(
        no_gravado + exento + neto_21 + neto_105 + neto_27
        + iva_21 + iva_105 + iva_27
        + perc_iva + perc_iibb + otros_imp,
        2,
    )

    if total_calculado <= 0 and payload.importe_total and payload.importe_total > 0:
        importe_total = round(float(payload.importe_total), 2)
        if info_tipo["letra"] in ("C", "E"):
            exento = importe_total
        else:
            neto_21 = round(importe_total / 1.21, 2)
            iva_21 = round(importe_total - neto_21, 2)
        total_calculado = importe_total

    if total_calculado <= 0:
        raise HTTPException(
            status_code=400,
            detail="El importe total del comprobante debe ser mayor a $ 0,00.",
        )

    if saldo_disponible_nc is not None and total_calculado > saldo_disponible_nc + 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El importe de la Nota de Crédito ($ {total_calculado:,.2f}) supera "
                f"el saldo pendiente del comprobante asociado ($ {saldo_disponible_nc:,.2f})."
            ),
        )

    fecha_eff = payload.fecha_emision or date.today()
    arca_service = ArcaService(use_mock=True)
    res_arca = arca_service.emitir_factura(
        punto_venta=payload.punto_venta,
        tipo_comprobante=payload.tipo_comprobante,
        importe_total=total_calculado,
        cuit_cliente=cuit_clean or (payload.cuit_cliente or "").strip() or None,
        fecha_emision=fecha_eff,
        db=db,
    )

    nueva_factura = Factura(
        cobranza_id=None,
        origen="FINANZAS",
        punto_venta=res_arca["punto_venta"],
        tipo_comprobante=res_arca["tipo_comprobante"],
        nro_comprobante=res_arca["nro_comprobante"],
        fecha_emision=res_arca["fecha_emision"],
        concepto_arca=payload.concepto_arca,
        fecha_servicio_desde=payload.fecha_servicio_desde or (fecha_eff if payload.concepto_arca in (2, 3) else None),
        fecha_servicio_hasta=payload.fecha_servicio_hasta or (fecha_eff if payload.concepto_arca in (2, 3) else None),
        fecha_vencimiento_pago=payload.fecha_vencimiento_pago or (fecha_eff if payload.concepto_arca in (2, 3) else None),
        tipo_doc_receptor=payload.tipo_doc_receptor,
        cuit_cliente=res_arca["cuit_cliente"],
        razon_social_receptor=payload.razon_social_receptor.strip() or "Consumidor Final",
        domicilio_receptor=(payload.domicilio_receptor or "").strip() or None,
        condicion_iva_receptor=payload.condicion_iva_receptor,
        provincia_id=payload.provincia_id,
        comprobante_asociado_id=payload.comprobante_asociado_id,
        comprobante_asociado_str=comp_asoc_str,
        cbu_emisor=payload.cbu_emisor,
        importe_no_gravado=no_gravado,
        importe_exento=exento,
        neto_gravado_21=neto_21,
        neto_gravado_105=neto_105,
        neto_gravado_27=neto_27,
        iva_21=iva_21,
        iva_105=iva_105,
        iva_27=iva_27,
        percepcion_iva=perc_iva,
        percepcion_iibb=perc_iibb,
        otros_impuestos=otros_imp,
        importe_total=total_calculado,
        cae=res_arca["cae"],
        vencimiento_cae=res_arca["vencimiento_cae"],
        items_detalle=items_serializados or None,
        observaciones=(payload.observaciones or "").strip() or None,
    )
    db.add(nueva_factura)
    db.commit()
    db.refresh(nueva_factura)

    return {
        "id": nueva_factura.id,
        "origen": nueva_factura.origen,
        "punto_venta": nueva_factura.punto_venta,
        "tipo_comprobante": nueva_factura.tipo_comprobante,
        "tipo_comprobante_nombre": info_tipo["nombre"],
        "letra": info_tipo["letra"],
        "nro_comprobante": nueva_factura.nro_comprobante,
        "comprobante_formateado": f"{nueva_factura.punto_venta:04d}-{nueva_factura.nro_comprobante:08d}",
        "fecha_emision": str(nueva_factura.fecha_emision),
        "cuit_cliente": nueva_factura.cuit_cliente,
        "razon_social_receptor": nueva_factura.razon_social_receptor,
        "importe_total": float(nueva_factura.importe_total),
        "cae": nueva_factura.cae,
        "vencimiento_cae": str(nueva_factura.vencimiento_cae) if nueva_factura.vencimiento_cae else None,
    }


@router.get("/emitidas")
def get_facturas_emitidas(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    tipo_comprobante: Optional[int] = None,
    origen: Optional[str] = None,
    punto_venta: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Lista los comprobantes ARCA emitidos con filtros y KPIs agregados del período.
    """
    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.cliente),
        joinedload(Factura.provincia),
    )

    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    if tipo_comprobante:
        query = query.filter(Factura.tipo_comprobante == tipo_comprobante)
    if origen and origen.upper() in ("FINANZAS", "COBRANZA"):
        query = query.filter(Factura.origen == origen.upper())
    if punto_venta:
        query = query.filter(Factura.punto_venta == punto_venta)

    facturas = query.order_by(Factura.fecha_emision.desc(), Factura.id.desc()).all()

    # Calcular Notas de Crédito emitidas asociadas a cada comprobante para determinar saldo pendiente / anulación total
    factura_ids = [f.id for f in facturas]
    nc_por_comprobante: dict[int, float] = {}
    if factura_ids:
        ncs_asociadas = (
            db.query(Factura.comprobante_asociado_id, Factura.importe_total)
            .filter(
                Factura.comprobante_asociado_id.in_(factura_ids),
                Factura.tipo_comprobante.in_(CODIGOS_NOTA_CREDITO),
            )
            .all()
        )
        for comp_id, imp in ncs_asociadas:
            if comp_id is not None:
                nc_por_comprobante[comp_id] = round(
                    nc_por_comprobante.get(comp_id, 0.0) + float(imp or 0.0), 2
                )

    items = []
    total_facturado_neto = 0.0
    total_iva_debito = 0.0
    total_notas_credito = 0.0

    search_lower = search.strip().lower() if search else None

    for f in facturas:
        info = get_info_tipo_comprobante(f.tipo_comprobante)
        bd = _extract_factura_breakdown(f)
        es_nc = f.tipo_comprobante in CODIGOS_NOTA_CREDITO
        signo = -1.0 if es_nc else 1.0

        razon_social = f.razon_social_receptor
        if not razon_social and f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito and f.cobranza.cuota.credito.cliente:
            cli = f.cobranza.cuota.credito.cliente
            razon_social = f"{cli.apellido}, {cli.nombre}"
        razon_social = razon_social or "Consumidor Final"

        cuit_str = f.cuit_cliente or "Consumidor Final"
        comp_fmt = f"{int(f.punto_venta):04d}-{int(f.nro_comprobante):08d}"

        if search_lower:
            haystack = f"{razon_social} {cuit_str} {comp_fmt} {info['nombre']} {f.cae or ''}".lower()
            if search_lower not in haystack:
                continue

        total_facturado_neto += signo * bd["importe_total"]
        total_iva_debito += signo * bd["iva_total"]
        if es_nc:
            total_notas_credito += bd["importe_total"]

        monto_nc_aplicado = 0.0 if es_nc else nc_por_comprobante.get(f.id, 0.0)
        saldo_pendiente_nc = (
            0.0 if es_nc else max(0.0, round(bd["importe_total"] - monto_nc_aplicado, 2))
        )
        anulada_por_nc = (not es_nc) and (bd["importe_total"] > 0) and (saldo_pendiente_nc <= 0.01)
        tiene_nc_parcial = (not es_nc) and (monto_nc_aplicado > 0.0) and not anulada_por_nc

        items.append({
            "id": f.id,
            "origen": f.origen or ("COBRANZA" if f.cobranza_id else "FINANZAS"),
            "cobranza_id": f.cobranza_id,
            "punto_venta": f.punto_venta,
            "tipo_comprobante": f.tipo_comprobante,
            "tipo_comprobante_nombre": info["nombre"],
            "letra": info["letra"],
            "es_nota_credito": es_nc,
            "nro_comprobante": f.nro_comprobante,
            "comprobante_formateado": comp_fmt,
            "fecha_emision": str(f.fecha_emision),
            "tipo_doc_receptor": f.tipo_doc_receptor or "CUIT",
            "cuit_cliente": f.cuit_cliente,
            "razon_social_receptor": razon_social,
            "condicion_iva_receptor": f.condicion_iva_receptor or "Consumidor Final",
            "provincia_id": f.provincia_id,
            "provincia_nombre": f.provincia.nombre if f.provincia else None,
            "comprobante_asociado_id": f.comprobante_asociado_id,
            "comprobante_asociado_str": f.comprobante_asociado_str,
            "importe_no_gravado": bd["importe_no_gravado"],
            "importe_exento": bd["importe_exento"],
            "neto_gravado": bd["neto_gravado_total"],
            "iva_total": bd["iva_total"],
            "otros_tributos": bd["otros_tributos_total"],
            "importe_total": bd["importe_total"],
            "monto_nc_aplicado": monto_nc_aplicado,
            "saldo_pendiente_nc": saldo_pendiente_nc,
            "anulada_por_nc": anulada_por_nc,
            "tiene_nc_parcial": tiene_nc_parcial,
            "cae": f.cae,
            "vencimiento_cae": str(f.vencimiento_cae) if f.vencimiento_cae else None,
            "observaciones": f.observaciones,
        })

    total = len(items)
    return {
        "items": items[skip : skip + limit],
        "total": total,
        "kpis": {
            "total_facturado_neto": round(total_facturado_neto, 2),
            "total_iva_debito": round(total_iva_debito, 2),
            "total_notas_credito": round(total_notas_credito, 2),
            "cantidad_comprobantes": total,
        },
    }


@router.get("/{factura_id:int}/pdf")
def descargar_pdf_individual(factura_id: int, db: Session = Depends(get_db)):
    """Descarga el PDF individual de cualquier comprobante emitido en ARCA."""
    factura = (
        db.query(Factura)
        .options(
            joinedload(Factura.cobranza)
            .joinedload(Cobranza.cuota)
            .joinedload(Cuota.credito)
            .joinedload(Credito.cliente)
        )
        .filter(Factura.id == factura_id)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")

    company_data_db = get_company_data(db)
    pdf_bytes = generar_factura_pdf_bytes(factura, company_data_db)
    info = get_info_tipo_comprobante(factura.tipo_comprobante)
    safe_tipo = info["nombre"].replace(" ", "_")
    filename = f"{safe_tipo}_{factura.punto_venta:04d}_{factura.nro_comprobante:08d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    db: Session = Depends(get_db),
):
    query = (
        db.query(Cobranza)
        .options(
            joinedload(Cobranza.cuota)
            .joinedload(Cuota.credito)
            .joinedload(Credito.socio_originador),
            joinedload(Cobranza.proceso),
        )
        .filter(Cobranza.facturada == False)
    )

    if fecha_emision_desde:
        query = query.filter(Cobranza.fecha >= fecha_emision_desde)
    if fecha_emision_hasta:
        query = query.filter(Cobranza.fecha <= fecha_emision_hasta)

    cobranzas = query.order_by(Cobranza.id.desc()).all()

    res = []
    for c in cobranzas:
        socio_nombre = "N/A"
        if c.cuota and c.cuota.credito and c.cuota.credito.socio_originador:
            socio_nombre = c.cuota.credito.socio_originador.razon_social

        if socios:
            socio_list = socios.split(",")
            if socio_nombre not in socio_list:
                continue

        vencimiento_cuota = (
            str(c.cuota.fecha_vencimiento) if c.cuota and c.cuota.fecha_vencimiento else ""
        )
        if fecha_vto_desde and vencimiento_cuota < fecha_vto_desde:
            continue
        if fecha_vto_hasta and vencimiento_cuota and vencimiento_cuota > fecha_vto_hasta:
            continue

        proceso_nombre = (
            f"Lote #{c.proceso.id} - {c.proceso.tipo.value if hasattr(c.proceso.tipo, 'value') else c.proceso.tipo}"
            if c.proceso
            else "Sin Proceso"
        )
        if procesos:
            procesos_list = procesos.split(",")
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
            "tipo_cobranza": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, "value") else str(c.tipo_cobranza),
            "socio_originador": socio_nombre,
            "vencimiento_cuota": vencimiento_cuota or None,
            "proceso_id": c.proceso_id,
            "proceso_nombre": proceso_nombre,
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
    cantidad = procesar_facturacion_pendiente(
        db, cobranza_ids=request.cobranza_ids, fecha_emision=request.fecha_emision
    )
    return {"message": f"Se procesaron {cantidad} facturas."}


@router.get("/libro-iva")
def descargar_libro_iva(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.socio_originador)
    )
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)

    facturas = query.order_by(Factura.fecha_emision.asc(), Factura.id.asc()).all()

    data = []
    for f in facturas:
        info = get_info_tipo_comprobante(f.tipo_comprobante)
        bd = _extract_factura_breakdown(f)
        signo = -1.0 if f.tipo_comprobante in CODIGOS_NOTA_CREDITO else 1.0

        cobranza = f.cobranza
        cuota = cobranza.cuota if cobranza else None
        credito = cuota.credito if cuota else None
        socio = credito.socio_originador if credito else None

        socio_nombre = socio.razon_social if socio else (f.razon_social_receptor or "Finanzas")
        nro_credito = credito.id if credito else "N/A"
        nro_cuota = cuota.nro_cuota if cuota else "N/A"

        data.append({
            "Fecha": f.fecha_emision.strftime("%d/%m/%Y"),
            "Origen": f.origen or ("COBRANZA" if f.cobranza_id else "FINANZAS"),
            "Tipo Comprobante": info["nombre"],
            "Punto Venta": f.punto_venta,
            "Nro Comprobante": f.nro_comprobante,
            "CUIT Cliente": f.cuit_cliente or "Consumidor Final",
            "Razón Social": f.razon_social_receptor or socio_nombre,
            "NO GRAVADO": round(signo * bd["importe_no_gravado"], 2),
            "EXENTO": round(signo * bd["importe_exento"], 2),
            "GRAVADO": round(signo * bd["neto_gravado_total"], 2),
            "IVA": round(signo * bd["iva_total"], 2),
            "OTROS TRIBUTOS": round(signo * bd["otros_tributos_total"], 2),
            "Importe Total": round(signo * bd["importe_total"], 2),
            "Socio Originador": socio_nombre,
            "Nro Crédito": nro_credito,
            "Nro Cuota": nro_cuota,
            "CAE": f.cae,
            "Vto CAE": f.vencimiento_cae.strftime("%d/%m/%Y") if f.vencimiento_cae else "",
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Libro IVA Ventas")

    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="libro_iva_ventas.xlsx"'}
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/descargar-masivo")
def descargar_pdfs_masivo(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db),
):
    company_data_db = get_company_data(db)

    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.cliente)
    )
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)

    facturas = query.all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for f in facturas:
            pdf_bytes = generar_factura_pdf_bytes(f, company_data_db)
            nro_credito_str = ""
            if f.cobranza and f.cobranza.cuota and f.cobranza.cuota.credito:
                nro_credito_str = f"_Credito_{f.cobranza.cuota.credito.id}"
            c_cuil_str = f"_CUIT_{f.cuit_cliente}" if f.cuit_cliente else ""
            info = get_info_tipo_comprobante(f.tipo_comprobante)
            safe_tipo = info["nombre"].replace(" ", "_")
            filename = f"{safe_tipo}_{f.punto_venta:04d}_{f.nro_comprobante:08d}{nro_credito_str}{c_cuil_str}.pdf"
            zip_file.writestr(filename, pdf_bytes)

    zip_buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="facturas.zip"'}
    return StreamingResponse(
        iter([zip_buffer.getvalue()]), media_type="application/zip", headers=headers
    )
