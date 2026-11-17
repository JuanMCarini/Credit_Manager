from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from datetime import date
import pandas as pd
import base64
import io
import json
import os
import re
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

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
from src.services.arca_service import (
    ArcaService,
    ArcaServiceError,
    CONDICIONES_IVA_RECEPTOR_CATALOGO,
    TIPOS_TRIBUTO_CATALOGO,
    get_arca_config,
    registrar_cae_contingencia,
    resolve_condicion_iva_receptor_id,
    validar_compatibilidad_iva_receptor_comprobante,
)
from src.services.arca_consulta import ArcaConsultaService
from src.config import get_company_data
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/facturacion", tags=["Facturación"])


def _extract_factura_breakdown(f: Factura) -> dict[str, float]:
    """
    Obtiene el desglose impositivo de una Factura.
    Si es una factura histórica de cobranza sin desglose propio cargado en las nuevas
    columnas, toma capital/interés/iva de la Cobranza vinculada.
    """
    no_gravado = float(f.importe_no_gravado or 0.0)
    exento = float(f.importe_exento or 0.0)
    neto_0 = float(getattr(f, "neto_gravado_0", 0.0) or 0.0)
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
        no_gravado + exento + neto_0 + neto_21 + neto_105 + neto_27
        + iva_21 + iva_105 + iva_27 + perc_iva + perc_iibb + otros_imp
    )
    if own_sum == 0.0 and f.cobranza is not None:
        no_gravado = float(f.cobranza.capital or 0.0)
        neto_21 = float(f.cobranza.interes or 0.0)
        iva_21 = float(f.cobranza.iva or 0.0)

    neto_gravado_total = round(neto_0 + neto_21 + neto_105 + neto_27, 2)
    iva_total = round(iva_21 + iva_105 + iva_27, 2)
    otros_tributos_total = round(perc_iva + perc_iibb + otros_imp, 2)
    importe_total = round(float(f.importe_total or 0.0), 2)

    return {
        "importe_no_gravado": round(no_gravado, 2),
        "importe_exento": round(exento, 2),
        "neto_gravado_0": round(neto_0, 2),
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


def generar_qr_afip_url(
    f: Factura,
    company_data_db,
    breakdown: dict[str, float] | None = None,
) -> str:
    """
    Construye la URL oficial del Código QR de ARCA/AFIP exigida por la RG 4892/2020:
    https://www.afip.gob.ar/fe/qr/?p=<payload_json_base64>
    """
    bd = breakdown or _extract_factura_breakdown(f)
    cfg_arca = get_arca_config()
    cuit_raw = cfg_arca.get("cuit") or getattr(company_data_db, "cuit", "") or "30000000000"
    cuit_emisor_digits = re.sub(r"\D", "", str(cuit_raw))
    cuit_emisor = int(cuit_emisor_digits) if cuit_emisor_digits else 30000000000

    doc_rec_digits = re.sub(r"\D", "", str(f.cuit_cliente or ""))
    t_doc_str = str(f.tipo_doc_receptor or "").upper().strip()
    if doc_rec_digits and len(doc_rec_digits) == 11:
        tipo_doc_rec = 86 if t_doc_str == "CUIL" else 80
        nro_doc_rec = int(doc_rec_digits)
    elif doc_rec_digits and len(doc_rec_digits) >= 7:
        tipo_doc_rec = 96
        nro_doc_rec = int(doc_rec_digits)
    else:
        tipo_doc_rec = 99
        nro_doc_rec = 0

    cae_digits = re.sub(r"\D", "", str(f.cae or "0"))
    cod_aut = int(cae_digits) if cae_digits else 0

    fecha_str = (
        f.fecha_emision.strftime("%Y-%m-%d")
        if hasattr(f.fecha_emision, "strftime")
        else str(f.fecha_emision)
    )

    qr_payload = {
        "ver": 1,
        "fecha": fecha_str,
        "cuit": cuit_emisor,
        "ptoVta": int(f.punto_venta or 1),
        "tipoCmp": int(f.tipo_comprobante or 1),
        "nroCmp": int(f.nro_comprobante or 1),
        "importe": round(float(bd["importe_total"]), 2),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": tipo_doc_rec,
        "nroDocRec": nro_doc_rec,
        "tipoCodAut": "E",
        "codAut": cod_aut,
    }

    qr_json = json.dumps(qr_payload, separators=(",", ":"))
    qr_b64 = base64.b64encode(qr_json.encode("utf-8")).decode("ascii")
    return f"https://www.afip.gob.ar/fe/qr/?p={qr_b64}"


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
    cfg_arca = get_arca_config()
    cond_emisor_label = cfg_arca.get("condicion_iva_emisor_label") or "IVA Responsable Inscripto"
    c_cuit = str(cfg_arca.get("cuit") or company_data_db.cuit or "")
    nro_iibb_str = str(cfg_arca.get("nro_iibb") or c_cuit)
    inicio_act_str = str(cfg_arca.get("inicio_actividades") or "01/01/2020")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, height - 5.5 * cm, f"Razón Social: {company_data_db.razon_social}")
    c.setFont("Helvetica", 9)
    c.drawString(1.5 * cm, height - 6.0 * cm, f"Domicilio Comercial: {company_data_db.domicilio}")
    c.drawString(1.5 * cm, height - 6.5 * cm, f"Condición frente al IVA: {cond_emisor_label}")

    c.setFont("Helvetica-Bold", 10)
    cuit_formateado = f"{c_cuit[:2]}-{c_cuit[2:10]}-{c_cuit[10:]}" if len(c_cuit) == 11 else c_cuit
    c.drawString(11 * cm, height - 5.5 * cm, f"CUIT: {cuit_formateado}")
    c.setFont("Helvetica", 9)
    c.drawString(11 * cm, height - 6.0 * cm, f"Ingresos Brutos: {nro_iibb_str}")
    c.drawString(11 * cm, height - 6.5 * cm, f"Fecha de Inicio de Actividades: {inicio_act_str}")

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

    # Código QR Reglamentario RG 4892/2020 + CAE y Vencimiento CAE
    qr_url = generar_qr_afip_url(f, company_data_db, breakdown=breakdown)
    qr_widget = QrCodeWidget(qr_url)
    bounds = qr_widget.getBounds()
    qr_w = bounds[2] - bounds[0]
    qr_h = bounds[3] - bounds[1]
    qr_size = 2.4 * cm
    qr_drawing = Drawing(
        qr_size,
        qr_size,
        transform=[qr_size / qr_w, 0, 0, qr_size / qr_h, 0, 0],
    )
    qr_drawing.add(qr_widget)
    renderPDF.draw(qr_drawing, c, 1.3 * cm, 1.15 * cm)

    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(4.0 * cm, 2.7 * cm, "Comprobante Autorizado por ARCA")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.0 * cm, 2.15 * cm, "CAE Nro:")
    c.setFont("Helvetica", 10)
    c.drawString(5.8 * cm, 2.15 * cm, f"{f.cae or '-'}")

    if f.vencimiento_cae:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(4.0 * cm, 1.65 * cm, "Fecha Vto. CAE:")
        c.setFont("Helvetica", 10)
        c.drawString(6.9 * cm, 1.65 * cm, f"{f.vencimiento_cae.strftime('%d/%m/%Y')}")

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

    return {
        "receptores": receptores,
        "provincias": provincias,
        "condiciones_iva_receptor": CONDICIONES_IVA_RECEPTOR_CATALOGO,
        "tipos_tributo": TIPOS_TRIBUTO_CATALOGO,
    }


@router.get("/condiciones-iva-receptor")
def get_condiciones_iva_receptor():
    """Retorna el catálogo oficial RG 5616 de Condición frente al IVA del Receptor."""
    return CONDICIONES_IVA_RECEPTOR_CATALOGO


@router.get("/tipos-tributo")
def get_tipos_tributo_arca():
    """Retorna el catálogo oficial de Tipos de Tributo ARCA (FEParamGetTiposTributos)."""
    try:
        return ArcaService().fe_param_get_tipos_tributos()
    except Exception:
        return TIPOS_TRIBUTO_CATALOGO


@router.get("/consultar-cuit/{cuit}")
def consultar_cuit_padron_arca(cuit: str, db: Session = Depends(get_db)):
    """
    Consulta el CUIT/CUIL en el Padrón de ARCA (ws_sr_constancia_inscripcion / getPersona_v2)
    y resuelve automáticamente Razón Social, Domicilio, Provincia y Condición frente al IVA.
    """
    try:
        svc = ArcaConsultaService()
        datos = svc.consultar_cuit(cuit)
    except ArcaServiceError as exc:
        raise HTTPException(status_code=exc.status_http or 400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar el Padrón de ARCA: {exc}",
        )

    prov_id = None
    prov_nombre_arca = str(datos.get("provincia") or "").strip().upper()
    if prov_nombre_arca:
        provincias_db = db.query(Provincia).all()
        for pr in provincias_db:
            p_nom = (pr.nombre or "").strip().upper()
            if p_nom and (p_nom in prov_nombre_arca or prov_nombre_arca in p_nom):
                prov_id = pr.id
                break
            if "CIUDAD AUTONOMA" in prov_nombre_arca and p_nom in ("CABA", "CAPITAL FEDERAL", "CIUDAD AUTONOMA DE BUENOS AIRES"):
                prov_id = pr.id
                break

    return {
        **datos,
        "provincia_id_sugerida": prov_id,
    }


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
    condicion_iva_receptor: Optional[str] = Field(default=None, max_length=60)
    condicion_iva_receptor_id: Optional[int] = None
    provincia_id: Optional[int] = None

    comprobante_asociado_id: Optional[int] = None
    comprobante_asociado_str: Optional[str] = Field(default=None, max_length=100)
    comprobante_asociado_tipo: Optional[int] = None
    comprobante_asociado_punto_venta: Optional[int] = None
    comprobante_asociado_nro: Optional[int] = None
    comprobante_asociado_fecha: Optional[date] = None

    cbu_emisor: Optional[str] = Field(default=None, max_length=22)
    fce_sistema_circulacion: Optional[str] = Field(default=None, max_length=10)
    fce_anulacion: Optional[str] = Field(default=None, max_length=5)

    importe_no_gravado: float = Field(default=0.0, ge=0)
    importe_exento: float = Field(default=0.0, ge=0)
    neto_gravado_0: float = Field(default=0.0, ge=0)
    neto_gravado_21: float = Field(default=0.0, ge=0)
    neto_gravado_105: float = Field(default=0.0, ge=0)
    neto_gravado_27: float = Field(default=0.0, ge=0)
    iva_21: Optional[float] = Field(default=None, ge=0)
    iva_105: Optional[float] = Field(default=None, ge=0)
    iva_27: Optional[float] = Field(default=None, ge=0)
    percepcion_iva: float = Field(default=0.0, ge=0)
    percepcion_iibb: float = Field(default=0.0, ge=0)
    otros_impuestos: float = Field(default=0.0, ge=0)
    tipo_tributo_otros_id: Optional[int] = Field(default=99)
    desc_tributo_otros: Optional[str] = Field(default="Otros Tributos", max_length=100)
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
    (Facturas A, B, C, M, Notas de Crédito, Notas de Débito, Recibos y FCE MiPyME).
    """
    if payload.tipo_comprobante not in TIPOS_COMPROBANTE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de comprobante ARCA inválido ({payload.tipo_comprobante}).",
        )

    info_tipo = TIPOS_COMPROBANTE_MAP[payload.tipo_comprobante]
    arca_service = ArcaService()

    # En entornos reales (Homologación / Producción), bloquear exportación (Clase E) y validar condición del emisor
    if not arca_service.use_mock and arca_service.environment != "mock":
        if info_tipo["letra"] == "E":
            raise HTTPException(
                status_code=400,
                detail="Los comprobantes de exportación (Clase E) están deshabilitados.",
            )

    cond_emisor = arca_service.config.get("condicion_iva_emisor", "RESPONSABLE_INSCRIPTO")
    if cond_emisor in ("MONOTRIBUTISTA", "EXENTO") and info_tipo["letra"] != "C":
        raise HTTPException(
            status_code=400,
            detail=(
                f"El emisor está configurado como {arca_service.config.get('condicion_iva_emisor_label', cond_emisor)} "
                "y únicamente puede emitir comprobantes Clase C."
            ),
        )

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
    comprobante_asociado_dict: dict[str, Any] | None = None
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
        comprobante_asociado_dict = {
            "tipo_comprobante": fact_asoc.tipo_comprobante,
            "punto_venta": fact_asoc.punto_venta,
            "nro_comprobante": fact_asoc.nro_comprobante,
            "fecha_emision": fact_asoc.fecha_emision,
        }

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
    elif payload.comprobante_asociado_nro:
        pv_asoc = int(payload.comprobante_asociado_punto_venta or payload.punto_venta)
        nro_asoc = int(payload.comprobante_asociado_nro)
        tipo_asoc = int(
            payload.comprobante_asociado_tipo
            or (1 if info_tipo["letra"] == "A" else 6 if info_tipo["letra"] == "B" else 11)
        )
        comprobante_asociado_dict = {
            "tipo_comprobante": tipo_asoc,
            "punto_venta": pv_asoc,
            "nro_comprobante": nro_asoc,
            "fecha_emision": payload.comprobante_asociado_fecha,
        }
        if not comp_asoc_str:
            info_asoc_m = get_info_tipo_comprobante(tipo_asoc)
            comp_asoc_str = f"{info_asoc_m['nombre']} {pv_asoc:04d}-{nro_asoc:08d}"

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
    neto_0 = round(float(payload.neto_gravado_0 or 0.0), 2)
    neto_21 = round(float(payload.neto_gravado_21 or 0.0), 2)
    neto_105 = round(float(payload.neto_gravado_105 or 0.0), 2)
    neto_27 = round(float(payload.neto_gravado_27 or 0.0), 2)

    items_serializados: list[dict] = []
    has_explicit_netos = (no_gravado + exento + neto_0 + neto_21 + neto_105 + neto_27) > 0

    bruto_21 = 0.0
    bruto_105 = 0.0
    bruto_27 = 0.0

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
                if info_tipo["letra"] in ("C", "E") or alicuota == "EXENTO":
                    exento = round(exento + sub, 2)
                elif alicuota == "0":
                    neto_0 = round(neto_0 + sub, 2)
                elif alicuota == "NO_GRAVADO":
                    no_gravado = round(no_gravado + sub, 2)
                elif alicuota == "10.5":
                    if info_tipo["discrimina_iva"]:
                        neto_105 = round(neto_105 + sub, 2)
                    else:
                        bruto_105 = round(bruto_105 + sub, 2)
                elif alicuota == "27":
                    if info_tipo["discrimina_iva"]:
                        neto_27 = round(neto_27 + sub, 2)
                    else:
                        bruto_27 = round(bruto_27 + sub, 2)
                else:
                    if info_tipo["discrimina_iva"]:
                        neto_21 = round(neto_21 + sub, 2)
                    else:
                        bruto_21 = round(bruto_21 + sub, 2)

    if info_tipo["letra"] in ("C", "E"):
        iva_21 = 0.0
        iva_105 = 0.0
        iva_27 = 0.0
    elif not info_tipo["discrimina_iva"] and not has_explicit_netos and (bruto_21 + bruto_105 + bruto_27) > 0:
        # En comprobantes B, calcular IVA por diferencia exacta (subtotal - neto) para evitar error de $0.01
        if bruto_21 > 0:
            neto_21 = round(bruto_21 / 1.21, 2)
            iva_21 = round(float(payload.iva_21) if payload.iva_21 is not None else (bruto_21 - neto_21), 2)
        else:
            iva_21 = 0.0
        if bruto_105 > 0:
            neto_105 = round(bruto_105 / 1.105, 2)
            iva_105 = round(float(payload.iva_105) if payload.iva_105 is not None else (bruto_105 - neto_105), 2)
        else:
            iva_105 = 0.0
        if bruto_27 > 0:
            neto_27 = round(bruto_27 / 1.27, 2)
            iva_27 = round(float(payload.iva_27) if payload.iva_27 is not None else (bruto_27 - neto_27), 2)
        else:
            iva_27 = 0.0
    else:
        iva_21 = round(float(payload.iva_21) if payload.iva_21 is not None else (neto_21 * 0.21), 2)
        iva_105 = round(float(payload.iva_105) if payload.iva_105 is not None else (neto_105 * 0.105), 2)
        iva_27 = round(float(payload.iva_27) if payload.iva_27 is not None else (neto_27 * 0.27), 2)

    perc_iva = round(float(payload.percepcion_iva or 0.0), 2)
    perc_iibb = round(float(payload.percepcion_iibb or 0.0), 2)
    otros_imp = round(float(payload.otros_impuestos or 0.0), 2)

    total_calculado = round(
        no_gravado + exento + neto_0 + neto_21 + neto_105 + neto_27
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
    doc_tipo_num = 80 if len(cuit_clean) == 11 else (96 if len(cuit_clean) >= 7 else 99)
    cond_iva_receptor_label = (payload.condicion_iva_receptor or "").strip() or (
        "Responsable Inscripto"
        if info_tipo["letra"] in ("A", "M")
        else ("Cliente del Exterior" if info_tipo["letra"] == "E" else "Consumidor Final")
    )
    cond_iva_id = resolve_condicion_iva_receptor_id(
        payload.condicion_iva_receptor_id or cond_iva_receptor_label,
        tipo_comprobante=payload.tipo_comprobante,
        doc_tipo=doc_tipo_num,
    )
    try:
        validar_compatibilidad_iva_receptor_comprobante(cond_iva_id, payload.tipo_comprobante)
    except ArcaServiceError as exc:
        raise HTTPException(status_code=exc.status_http or 400, detail=str(exc))

    try:
        res_arca = arca_service.emitir_factura(
            punto_venta=payload.punto_venta,
            tipo_comprobante=payload.tipo_comprobante,
            importe_total=total_calculado,
            cuit_cliente=cuit_clean or (payload.cuit_cliente or "").strip() or None,
            fecha_emision=fecha_eff,
            db=db,
            concepto_arca=payload.concepto_arca,
            tipo_doc_receptor=payload.tipo_doc_receptor,
            condicion_iva_receptor=cond_iva_receptor_label,
            condicion_iva_receptor_id=cond_iva_id,
            comprobante_asociado=comprobante_asociado_dict,
            comprobante_asociado_str=comp_asoc_str,
            cbu_emisor=payload.cbu_emisor,
            fce_sistema_circulacion=payload.fce_sistema_circulacion,
            fce_anulacion=payload.fce_anulacion,
            importe_no_gravado=no_gravado,
            importe_exento=exento,
            neto_gravado_0=neto_0,
            neto_gravado_21=neto_21,
            neto_gravado_105=neto_105,
            neto_gravado_27=neto_27,
            iva_21=iva_21,
            iva_105=iva_105,
            iva_27=iva_27,
            percepcion_iva=perc_iva,
            percepcion_iibb=perc_iibb,
            otros_impuestos=otros_imp,
            tipo_tributo_otros_id=payload.tipo_tributo_otros_id,
            desc_tributo_otros=payload.desc_tributo_otros,
            otros_tributos=round(perc_iva + perc_iibb + otros_imp, 2),
            fecha_servicio_desde=payload.fecha_servicio_desde,
            fecha_servicio_hasta=payload.fecha_servicio_hasta,
            fecha_vencimiento_pago=payload.fecha_vencimiento_pago,
        )
    except ArcaServiceError as exc:
        raise HTTPException(status_code=exc.status_http or 400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    fecha_serv_desde = payload.fecha_servicio_desde or (fecha_eff if payload.concepto_arca in (2, 3) else None)
    fecha_serv_hasta = payload.fecha_servicio_hasta or (fecha_eff if payload.concepto_arca in (2, 3) else None)
    fecha_vto_pago = payload.fecha_vencimiento_pago or (fecha_eff if payload.concepto_arca in (2, 3) else None)
    razon_social_rec = payload.razon_social_receptor.strip() or "Consumidor Final"
    domicilio_rec = (payload.domicilio_receptor or "").strip() or None
    cbu_emisor_val = payload.cbu_emisor or arca_service.config.get("cbu_fce_default") or None
    estado_arca_val = "MOCK" if arca_service.use_mock else f"AUTORIZADA_{arca_service.environment.upper()}"
    obs_val = (payload.observaciones or "").strip() or None

    nueva_factura = Factura(
        cobranza_id=None,
        origen="FINANZAS",
        punto_venta=res_arca["punto_venta"],
        tipo_comprobante=res_arca["tipo_comprobante"],
        nro_comprobante=res_arca["nro_comprobante"],
        fecha_emision=res_arca["fecha_emision"],
        concepto_arca=payload.concepto_arca,
        fecha_servicio_desde=fecha_serv_desde,
        fecha_servicio_hasta=fecha_serv_hasta,
        fecha_vencimiento_pago=fecha_vto_pago,
        tipo_doc_receptor=payload.tipo_doc_receptor,
        cuit_cliente=res_arca["cuit_cliente"],
        razon_social_receptor=razon_social_rec,
        domicilio_receptor=domicilio_rec,
        condicion_iva_receptor=cond_iva_receptor_label,
        condicion_iva_receptor_id=cond_iva_id,
        provincia_id=payload.provincia_id,
        comprobante_asociado_id=payload.comprobante_asociado_id,
        comprobante_asociado_str=comp_asoc_str,
        cbu_emisor=cbu_emisor_val,
        importe_no_gravado=no_gravado,
        importe_exento=exento,
        neto_gravado_0=neto_0,
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
        estado_arca=estado_arca_val,
        items_detalle=items_serializados or None,
        observaciones=obs_val,
    )
    try:
        db.add(nueva_factura)
        db.commit()
        db.refresh(nueva_factura)
    except Exception as db_exc:
        db.rollback()
        registrar_cae_contingencia(
            res_arca,
            str(db_exc),
            extra_data={
                "origen": "FINANZAS",
                "concepto_arca": payload.concepto_arca,
                "fecha_servicio_desde": fecha_serv_desde,
                "fecha_servicio_hasta": fecha_serv_hasta,
                "fecha_vencimiento_pago": fecha_vto_pago,
                "tipo_doc_receptor": payload.tipo_doc_receptor,
                "razon_social_receptor": razon_social_rec,
                "domicilio_receptor": domicilio_rec,
                "condicion_iva_receptor": cond_iva_receptor_label,
                "condicion_iva_receptor_id": cond_iva_id,
                "provincia_id": payload.provincia_id,
                "comprobante_asociado_id": payload.comprobante_asociado_id,
                "comprobante_asociado_str": comp_asoc_str,
                "cbu_emisor": cbu_emisor_val,
                "importe_no_gravado": no_gravado,
                "importe_exento": exento,
                "neto_gravado_0": neto_0,
                "neto_gravado_21": neto_21,
                "neto_gravado_105": neto_105,
                "neto_gravado_27": neto_27,
                "iva_21": iva_21,
                "iva_105": iva_105,
                "iva_27": iva_27,
                "percepcion_iva": perc_iva,
                "percepcion_iibb": perc_iibb,
                "otros_impuestos": otros_imp,
                "estado_arca": estado_arca_val,
                "items_detalle": items_serializados or None,
                "observaciones": obs_val,
            },
        )
        logger.critical(
            f"[ARCA CRITICAL] Comprobante autorizado en ARCA pero falló el guardado en BD: "
            f"PV={res_arca['punto_venta']} Tipo={res_arca['tipo_comprobante']} "
            f"Nro={res_arca['nro_comprobante']} CAE={res_arca['cae']} "
            f"Vto={res_arca['vencimiento_cae']} Total={total_calculado} Error={db_exc}"
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"El comprobante fue autorizado en ARCA (Nro {res_arca['punto_venta']:04d}-{res_arca['nro_comprobante']:08d}, "
                f"CAE {res_arca['cae']}), pero ocurrió un error al guardar en la base de datos: {db_exc}"
            ),
        )

    return {
        "id": nueva_factura.id,
        "origen": nueva_factura.origen,
        "environment": arca_service.environment,
        "punto_venta": nueva_factura.punto_venta,
        "tipo_comprobante": nueva_factura.tipo_comprobante,
        "tipo_comprobante_nombre": info_tipo["nombre"],
        "letra": info_tipo["letra"],
        "nro_comprobante": nueva_factura.nro_comprobante,
        "comprobante_formateado": f"{nueva_factura.punto_venta:04d}-{nueva_factura.nro_comprobante:08d}",
        "fecha_emision": str(nueva_factura.fecha_emision),
        "cuit_cliente": nueva_factura.cuit_cliente,
        "razon_social_receptor": nueva_factura.razon_social_receptor,
        "condicion_iva_receptor": nueva_factura.condicion_iva_receptor,
        "condicion_iva_receptor_id": nueva_factura.condicion_iva_receptor_id,
        "importe_no_gravado": float(nueva_factura.importe_no_gravado or 0.0),
        "importe_exento": float(nueva_factura.importe_exento or 0.0),
        "neto_gravado_0": float(nueva_factura.neto_gravado_0 or 0.0),
        "neto_gravado_21": float(nueva_factura.neto_gravado_21 or 0.0),
        "neto_gravado_105": float(nueva_factura.neto_gravado_105 or 0.0),
        "neto_gravado_27": float(nueva_factura.neto_gravado_27 or 0.0),
        "iva_21": float(nueva_factura.iva_21 or 0.0),
        "iva_105": float(nueva_factura.iva_105 or 0.0),
        "iva_27": float(nueva_factura.iva_27 or 0.0),
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
    incluir_mock: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    Lista los comprobantes ARCA emitidos con filtros y KPIs agregados del período.
    """
    cfg = get_arca_config()
    env_actual = str(cfg.get("environment") or "mock").lower()

    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.cliente),
        joinedload(Factura.provincia),
    )

    if incluir_mock is False or (incluir_mock is None and env_actual == "produccion"):
        query = query.filter(or_(Factura.estado_arca.is_(None), Factura.estado_arca != "MOCK"))

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

        estado_arca_val = f.estado_arca or "MOCK"
        incluir_en_kpi = env_actual == "mock" or estado_arca_val != "MOCK"
        if incluir_en_kpi:
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
            "estado_arca": estado_arca_val,
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
def get_ultima_fecha_factura(
    punto_venta: Optional[int] = None,
    tipo_comprobante: Optional[int] = None,
    db: Session = Depends(get_db),
):
    cfg = get_arca_config()
    query = db.query(Factura)
    if cfg.get("environment") in ("homologacion", "produccion"):
        query = query.filter(or_(Factura.estado_arca.is_(None), Factura.estado_arca != "MOCK"))
    if punto_venta is not None:
        query = query.filter(Factura.punto_venta == punto_venta)
    if tipo_comprobante is not None:
        query = query.filter(Factura.tipo_comprobante == tipo_comprobante)
    ultima = query.order_by(Factura.fecha_emision.desc(), Factura.id.desc()).first()
    return {"ultima_fecha": str(ultima.fecha_emision) if ultima else None}


class ProcesarRequest(BaseModel):
    cobranza_ids: Optional[List[int]] = None
    fecha_emision: Optional[date] = None
    punto_venta: Optional[int] = Field(default=None, ge=1, le=99999)
    tipo_comprobante: Optional[int] = None
    confirmar_real: bool = False


@router.post("/procesar")
def procesar_facturacion(request: ProcesarRequest, db: Session = Depends(get_db)):
    cfg = get_arca_config()
    if cfg.get("environment") in ("homologacion", "produccion") and not request.confirmar_real:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El sistema está en modo '{cfg.get('environment').upper()}'. "
                "Debe confirmar explícitamente la emisión de facturas reales (confirmar_real=true)."
            ),
        )
    res_lote = procesar_facturacion_pendiente(
        db,
        cobranza_ids=request.cobranza_ids,
        fecha_emision=request.fecha_emision,
        punto_venta=request.punto_venta,
        tipo_comprobante=request.tipo_comprobante,
        retornar_detalle=True,
    )
    cantidad = res_lote["procesadas"]
    errores = res_lote["errores"]
    msg = f"Se procesaron {cantidad} facturas."
    if res_lote.get("lote_abortado"):
        msg += (
            f" Lote detenido automáticamente por error global de conexión/configuración con ARCA: "
            f"{res_lote.get('motivo_aborto')}"
        )
    elif errores:
        msg += f" ({len(errores)} con error)."
    return {
        "message": msg,
        **res_lote,
    }


@router.get("/libro-iva")
def descargar_libro_iva(
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db),
):
    cfg = get_arca_config()
    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.socio_originador)
    )
    if cfg.get("environment") in ("homologacion", "produccion"):
        query = query.filter(or_(Factura.estado_arca.is_(None), Factura.estado_arca != "MOCK"))
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
    cfg = get_arca_config()

    query = db.query(Factura).options(
        joinedload(Factura.cobranza)
        .joinedload(Cobranza.cuota)
        .joinedload(Cuota.credito)
        .joinedload(Credito.cliente)
    )
    if cfg.get("environment") in ("homologacion", "produccion"):
        query = query.filter(or_(Factura.estado_arca.is_(None), Factura.estado_arca != "MOCK"))
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
