import difflib
import html
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict

import httpx
import pandas as pd

from src.config import COMPANY_DATA
from src.services.arca_service import (
    ArcaServiceError,
    _clean_cuit,
    _find_text_local,
    _strip_ns,
    get_arca_config,
    login_cms_wsaa,
)

logger = logging.getLogger(__name__)

PADRON_A5_URLS = {
    "homologacion": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5",
    "produccion": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5",
}

PADRON_A5_NS = "http://a5.soap.ws.server.puc.sr/"


def _find_child_local(elem: ET.Element | None, local_name: str) -> ET.Element | None:
    if elem is None:
        return None
    for child in elem:
        if _strip_ns(child.tag) == local_name:
            return child
    return None


def _findall_children_local(elem: ET.Element | None, local_name: str) -> list[ET.Element]:
    if elem is None:
        return []
    return [child for child in elem if _strip_ns(child.tag) == local_name]


class ArcaConsultaService:
    """
    Servicio de consulta de CUIT/CUIL en el padrón de ARCA/AFIP
    (ws_sr_constancia_inscripcion / getPersona_v2).
    Soporta modo mock (simulado) y conexión SOAP real en homologación/producción.
    """

    def __init__(self, use_mock: bool | None = None):
        cfg = get_arca_config()
        self.config = cfg
        if use_mock is None:
            self.environment = cfg.get("environment", "mock")
            self.use_mock = self.environment == "mock"
        else:
            self.use_mock = bool(use_mock)
            self.environment = "mock" if self.use_mock else cfg.get("environment", "homologacion")
            if not self.use_mock and self.environment == "mock":
                self.environment = "homologacion"

    def consultar_cuit(self, cuit: int | str) -> Dict[str, Any]:
        """
        Consulta los datos de un CUIT/CUIL en ARCA (ws_sr_constancia_inscripcion / getPersona_v2).
        """
        clean_cuit = _clean_cuit(cuit)
        if len(clean_cuit) != 11:
            raise ArcaServiceError(
                "El CUIT/CUIL a consultar debe contener exactamente 11 dígitos numéricos.",
                status_http=400,
            )
        cuit_int = int(clean_cuit)

        if self.use_mock or self.environment == "mock":
            logger.info(f"[ARCA MOCK] Consultando datos del padrón para el CUIT/CUIL: {clean_cuit}")
            es_fisica = clean_cuit.startswith(("20", "23", "24", "27"))
            razon_social = "PEREZ JUAN (MOCK)" if es_fisica else "MOCK EMPRESA S.A."
            cond_iva = "Monotributista" if es_fisica else "Responsable Inscripto"
            cond_iva_id = 6 if es_fisica else 1

            return {
                "idPersona": cuit_int,
                "cuit": clean_cuit,
                "tipoPersona": "FISICA" if es_fisica else "JURIDICA",
                "estadoClave": "ACTIVO",
                "nombre": "MOCK PEREZ JUAN" if es_fisica else "MOCK EMPRESA S.A.",
                "apellido": "PEREZ" if es_fisica else None,
                "razon_social": razon_social,
                "domicilio_fiscal": "AV MOCK 123",
                "localidad": "CIUDAD AUTONOMA BUENOS AIRES",
                "codigo_postal": "1000",
                "provincia": "CIUDAD AUTONOMA BUENOS AIRES",
                "condicion_iva": cond_iva,
                "condicion_iva_receptor_id": cond_iva_id,
                "environment": "mock",
                "domicilio": [
                    {
                        "tipoDomicilio": "FISCAL",
                        "direccion": "AV MOCK 123",
                        "localidad": "CIUDAD AUTONOMA BUENOS AIRES",
                        "codPostal": "1000",
                        "idProvincia": 0,
                        "descripcionProvincia": "CIUDAD AUTONOMA BUENOS AIRES",
                    }
                ],
                "impuestos": [
                    {
                        "idImpuesto": 10,
                        "descImpuesto": "Ganancias Sociedades"
                        if not es_fisica
                        else "Ganancias Personas Fisicas",
                    },
                    {"idImpuesto": 20 if es_fisica else 30, "descImpuesto": "Monotributo" if es_fisica else "IVA"},
                ],
                "monotributo": {"categoria": "A", "actividad": "Servicios"} if es_fisica else None,
            }

        if self.environment not in PADRON_A5_URLS:
            raise ArcaServiceError(f"Entorno de Padrón ARCA inválido: {self.environment}", status_http=400)

        ta = login_cms_wsaa(self.environment, service="ws_sr_constancia_inscripcion")
        cuit_rep = _clean_cuit(self.config.get("cuit") or COMPANY_DATA.cuit)

        soap_envelope = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            f'xmlns:a5="{PADRON_A5_NS}">'
            "<soapenv:Header/>"
            "<soapenv:Body>"
            "<a5:getPersona_v2>"
            f"<token>{html.escape(ta['token'])}</token>"
            f"<sign>{html.escape(ta['sign'])}</sign>"
            f"<cuitRepresentada>{cuit_rep}</cuitRepresentada>"
            f"<idPersona>{clean_cuit}</idPersona>"
            "</a5:getPersona_v2>"
            "</soapenv:Body>"
            "</soapenv:Envelope>"
        )

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    PADRON_A5_URLS[self.environment],
                    content=soap_envelope.encode("utf-8"),
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ArcaServiceError(
                f"Error de red al consultar Padrón ARCA ({self.environment}): {exc}",
                status_http=502,
            ) from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise ArcaServiceError(
                f"Respuesta no-XML del servicio de Padrón ARCA (HTTP {response.status_code}).",
                status_http=502,
            ) from exc

        fault_string = _find_text_local(root, "faultstring")
        if fault_string:
            raise ArcaServiceError(
                f"Error SOAP Padrón ARCA ({self.environment}): {fault_string}",
                status_http=400,
            )

        persona_return = None
        for elem in root.iter():
            if _strip_ns(elem.tag) == "personaReturn":
                persona_return = elem
                break

        if persona_return is None:
            raise ArcaServiceError(
                "Respuesta inválida de Padrón ARCA: no se encontró el nodo personaReturn.",
                status_http=502,
            )

        datos_gen = _find_child_local(persona_return, "datosGenerales")
        err_constancia = _find_child_local(persona_return, "errorConstancia")
        if datos_gen is None:
            err_msgs: list[str] = []
            if err_constancia is not None:
                for child in err_constancia.iter():
                    if _strip_ns(child.tag) == "error" and child.text:
                        err_msgs.append(child.text.strip())
            detalle = "; ".join(err_msgs) if err_msgs else f"CUIT {clean_cuit} inexistente o con error de constancia en ARCA."
            raise ArcaServiceError(detalle, status_http=404)

        tipo_persona = (_find_text_local(datos_gen, "tipoPersona") or "JURIDICA").upper()
        estado_clave = (_find_text_local(datos_gen, "estadoClave") or "ACTIVO").upper()
        razon_social_xml = _find_text_local(datos_gen, "razonSocial") or ""
        apellido_xml = _find_text_local(datos_gen, "apellido") or ""
        nombre_xml = _find_text_local(datos_gen, "nombre") or ""

        if razon_social_xml:
            razon_social = razon_social_xml
        else:
            razon_social = f"{apellido_xml} {nombre_xml}".strip() or clean_cuit

        dom_fiscal = _find_child_local(datos_gen, "domicilioFiscal")
        direccion = ""
        localidad = ""
        cod_postal = ""
        id_prov = 0
        desc_prov = ""
        if dom_fiscal is not None:
            direccion = (
                _find_text_local(dom_fiscal, "direccion")
                or _find_text_local(dom_fiscal, "dirección")
                or ""
            )
            localidad = _find_text_local(dom_fiscal, "localidad") or ""
            cod_postal = _find_text_local(dom_fiscal, "codPostal") or ""
            id_prov_str = _find_text_local(dom_fiscal, "idProvincia")
            id_prov = int(id_prov_str) if id_prov_str and id_prov_str.isdigit() else 0
            desc_prov = _find_text_local(dom_fiscal, "descripcionProvincia") or ""

        # Impuestos en Régimen General
        datos_rg = _find_child_local(persona_return, "datosRegimenGeneral")
        impuestos_list: list[dict[str, Any]] = []
        ids_impuestos: set[int] = set()
        for imp_el in _findall_children_local(datos_rg, "impuesto"):
            id_imp_str = _find_text_local(imp_el, "idImpuesto")
            desc_imp = _find_text_local(imp_el, "descripcionImpuesto") or ""
            if id_imp_str and id_imp_str.isdigit():
                id_imp = int(id_imp_str)
                ids_impuestos.add(id_imp)
                impuestos_list.append({"idImpuesto": id_imp, "descImpuesto": desc_imp})

        # Monotributo
        datos_mono = _find_child_local(persona_return, "datosMonotributo")
        mono_info = None
        if datos_mono is not None:
            cat_el = _find_child_local(datos_mono, "categoriaMonotributo")
            cat_desc = _find_text_local(cat_el, "descripcionCategoria") if cat_el is not None else None
            act_el = _find_child_local(datos_mono, "actividadMonotributista")
            act_desc = _find_text_local(act_el, "descripcionActividad") if act_el is not None else None
            for imp_m in _findall_children_local(datos_mono, "impuesto"):
                id_m_str = _find_text_local(imp_m, "idImpuesto")
                if id_m_str and id_m_str.isdigit():
                    ids_impuestos.add(int(id_m_str))
            if cat_el is not None or ids_impuestos.intersection({20, 21, 22, 23, 24}):
                mono_info = {
                    "categoria": cat_desc or "MONOTRIBUTO",
                    "actividad": act_desc or "",
                }

        # Determinar Condición frente al IVA y su código RG 5616
        if 30 in ids_impuestos:
            condicion_iva = "Responsable Inscripto"
            condicion_iva_id = 1
        elif mono_info is not None or ids_impuestos.intersection({20, 21, 22, 23, 24}):
            condicion_iva = "Monotributista"
            condicion_iva_id = 6
        elif 32 in ids_impuestos:
            condicion_iva = "IVA Exento"
            condicion_iva_id = 4
        elif 34 in ids_impuestos or 33 in ids_impuestos:
            condicion_iva = "IVA No Alcanzado"
            condicion_iva_id = 15
        else:
            condicion_iva = "Consumidor Final" if tipo_persona == "FISICA" else "IVA No Alcanzado"
            condicion_iva_id = 5 if tipo_persona == "FISICA" else 15

        return {
            "idPersona": cuit_int,
            "cuit": clean_cuit,
            "tipoPersona": tipo_persona,
            "estadoClave": estado_clave,
            "nombre": nombre_xml or razon_social,
            "apellido": apellido_xml or None,
            "razon_social": razon_social,
            "domicilio_fiscal": direccion,
            "localidad": localidad,
            "codigo_postal": cod_postal,
            "provincia": desc_prov,
            "condicion_iva": condicion_iva,
            "condicion_iva_receptor_id": condicion_iva_id,
            "environment": self.environment,
            "domicilio": [
                {
                    "tipoDomicilio": "FISCAL",
                    "direccion": direccion,
                    "localidad": localidad,
                    "codPostal": cod_postal,
                    "idProvincia": id_prov,
                    "descripcionProvincia": desc_prov,
                }
            ]
            if (direccion or localidad or desc_prov)
            else [],
            "impuestos": impuestos_list,
            "monotributo": mono_info,
        }


def validar_datos_arca(df_invs: pd.DataFrame):
    """
    Valida que los nombres y CUITs de los inversores en el DataFrame coincidan
    con los registros de ARCA/AFIP.
    """
    arca_service = ArcaConsultaService()

    if arca_service.use_mock:
        print(
            "⚠️ [ADVERTENCIA] ARCA en modo MOCK: Se omitirá la verificación de identidad (Razón Social vs CUIT) para no inundar la consola."
        )

    errores_validacion = []

    for _, row in df_invs.iterrows():
        val = row["CUIT/CUIL"]
        if pd.isna(val):
            errores_validacion.append(f"Falta CUIT/CUIL para '{row['Razón Social']}'")
            continue

        if isinstance(val, float):
            cuit = str(int(val))
        else:
            cuit = str(val).replace("-", "").strip()
            if cuit.endswith(".0"):
                cuit = cuit[:-2]

        razon_social_excel = str(row["Razón Social"]).strip().upper()

        if not cuit.isdigit():
            errores_validacion.append(f"CUIT/CUIL inválido: {row['CUIT/CUIL']}")
            continue

        if arca_service.use_mock:
            continue

        cuit_int = int(cuit)
        try:
            datos_arca = arca_service.consultar_cuit(cuit_int)
        except Exception as exc:
            errores_validacion.append(f"CUIT {cuit}: {exc}")
            continue

        if "error" in datos_arca:
            errores_validacion.append(f"CUIT {cuit} no encontrado en ARCA.")
            continue

        nombre_arca = str(datos_arca.get("razon_social") or datos_arca.get("nombre", "")).upper()
        if datos_arca.get("tipoPersona") == "FISICA" and datos_arca.get("apellido"):
            ap = str(datos_arca.get("apellido")).upper()
            nom = str(datos_arca.get("nombre")).upper()
            if ap not in nombre_arca:
                nombre_arca = f"{ap} {nom}".strip()

        similitud = difflib.SequenceMatcher(None, razon_social_excel, nombre_arca).ratio()

        if (
            similitud < 0.6
            and razon_social_excel not in nombre_arca
            and nombre_arca not in razon_social_excel
        ):
            errores_validacion.append(
                f"Discrepancia en CUIT {cuit}: Excel dice '{razon_social_excel}', "
                f"ARCA dice '{nombre_arca}'"
            )

    if errores_validacion:
        raise ValueError("Falló la validación con ARCA:\n" + "\n".join(errores_validacion))
