import base64
import html
import json
import logging
import random
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID
from sqlalchemy import func

from src.config import COMPANY_DATA, ROOT_DIR

logger = logging.getLogger(__name__)

ARCA_CERTS_DIR = ROOT_DIR / "data" / "certs" / "arca"
ARCA_CONFIG_PATH = ARCA_CERTS_DIR / "arca_config.json"
ARCA_KEY_PATH = ARCA_CERTS_DIR / "arca.key"
ARCA_CSR_PATH = ARCA_CERTS_DIR / "arca.csr"
ARCA_CRT_PATH = ARCA_CERTS_DIR / "arca.crt"
ARCA_TA_CACHE_PATH = ARCA_CERTS_DIR / "arca_ta_cache.json"

VALID_ENVIRONMENTS = ("mock", "homologacion", "produccion")
DEFAULT_DIAS_ALERTA_VENCIMIENTO = 5

WSAA_URLS = {
    "homologacion": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
    "produccion": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
}

WSFEV1_URLS = {
    "homologacion": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
    "produccion": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
}

FEV1_NS = "http://ar.gov.afip.dif.FEV1/"


def _ensure_arca_dir() -> Path:
    """Crea el directorio local data/certs/arca/ si no existe."""
    ARCA_CERTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARCA_CERTS_DIR


def _clean_cuit(cuit: str | int | None) -> str:
    """Limpia guiones o espacios y retorna solo los dígitos del CUIT."""
    if cuit is None:
        return ""
    return "".join(filter(str.isdigit, str(cuit)))


def get_arca_config() -> dict[str, Any]:
    """
    Lee la configuración local de ARCA desde data/certs/arca/arca_config.json.
    Si no existe, crea el directorio y retorna la configuración por defecto.
    """
    _ensure_arca_dir()
    default_config: dict[str, Any] = {
        "environment": "mock",
        "cuit": _clean_cuit(COMPANY_DATA.cuit) or "30000000000",
        "punto_venta_default": 1,
        "dias_alerta_vencimiento": DEFAULT_DIAS_ALERTA_VENCIMIENTO,
    }

    if not ARCA_CONFIG_PATH.exists():
        return default_config

    try:
        raw = json.loads(ARCA_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_config
    except Exception as exc:
        logger.warning(f"No se pudo leer arca_config.json, usando valores por defecto: {exc}")
        return default_config

    env_val = str(raw.get("environment", default_config["environment"])).strip().lower()
    if env_val not in VALID_ENVIRONMENTS:
        env_val = "mock"

    cuit_val = _clean_cuit(raw.get("cuit", default_config["cuit"]))
    try:
        pv_val = int(raw.get("punto_venta_default", default_config["punto_venta_default"]))
    except (TypeError, ValueError):
        pv_val = 1

    try:
        dias_alerta = int(
            raw.get("dias_alerta_vencimiento", default_config["dias_alerta_vencimiento"])
        )
    except (TypeError, ValueError):
        dias_alerta = DEFAULT_DIAS_ALERTA_VENCIMIENTO

    return {
        "environment": env_val,
        "cuit": cuit_val,
        "punto_venta_default": pv_val,
        "dias_alerta_vencimiento": dias_alerta,
    }


def save_arca_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Guarda y valida la configuración local de ARCA en data/certs/arca/arca_config.json.
    Campos: environment ("mock" | "homologacion" | "produccion"), cuit,
    punto_venta_default y dias_alerta_vencimiento (por defecto 5).
    """
    if not isinstance(data, dict):
        raise ValueError("Los datos de configuración deben ser un diccionario.")

    _ensure_arca_dir()
    current = get_arca_config()

    env_raw = data.get("environment", current["environment"])
    env_val = str(env_raw).strip().lower()
    if env_val not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"Entorno inválido '{env_raw}'. Valores permitidos: {', '.join(VALID_ENVIRONMENTS)}."
        )

    if "cuit" in data and data["cuit"] is not None and str(data["cuit"]).strip() != "":
        cuit_val = _clean_cuit(data["cuit"])
        if len(cuit_val) != 11:
            raise ValueError("El CUIT debe contener exactamente 11 dígitos numéricos.")
    else:
        cuit_val = current["cuit"]

    pv_raw = data.get("punto_venta_default", current["punto_venta_default"])
    try:
        pv_val = int(pv_raw)
        if pv_val < 1:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("El punto de venta por defecto debe ser un entero mayor o igual a 1.")

    dias_raw = data.get(
        "dias_alerta_vencimiento",
        current.get("dias_alerta_vencimiento", DEFAULT_DIAS_ALERTA_VENCIMIENTO),
    )
    if dias_raw is None:
        dias_val = DEFAULT_DIAS_ALERTA_VENCIMIENTO
    else:
        try:
            dias_val = int(dias_raw)
            if dias_val < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(
                "El campo dias_alerta_vencimiento debe ser un entero mayor o igual a 0."
            )

    new_config = {
        "environment": env_val,
        "cuit": cuit_val,
        "punto_venta_default": pv_val,
        "dias_alerta_vencimiento": dias_val,
    }

    ARCA_CONFIG_PATH.write_text(
        json.dumps(new_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return new_config


def generar_key_y_csr(cuit: str | int, razon_social: str, alias: str) -> dict[str, Any]:
    """
    Genera una clave privada RSA de 2048 bits (arca.key) y una solicitud de firma
    de certificado (arca.csr) usando cryptography.x509 con los atributos fiscales
    estándar de Argentina:
      C=AR, O=<razon_social>, CN=<alias>, serialNumber=CUIT <cuit>
    """
    clean_cuit = _clean_cuit(cuit)
    if len(clean_cuit) != 11:
        raise ValueError("El CUIT debe contener exactamente 11 dígitos numéricos.")

    razon_clean = str(razon_social or "").strip()
    if not razon_clean:
        raise ValueError("La razón social es obligatoria para generar el CSR.")

    alias_clean = str(alias or "").strip()
    if not alias_clean:
        raise ValueError("El alias (Common Name) es obligatorio para generar el CSR.")

    _ensure_arca_dir()

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, razon_clean),
            x509.NameAttribute(NameOID.COMMON_NAME, alias_clean),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CUIT {clean_cuit}"),
        ]
    )

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .sign(private_key, hashes.SHA256())
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    ARCA_KEY_PATH.write_bytes(key_pem)
    ARCA_CSR_PATH.write_bytes(csr_pem)

    return {
        "key_path": str(ARCA_KEY_PATH),
        "csr_path": str(ARCA_CSR_PATH),
        "key_pem": key_pem.decode("utf-8"),
        "csr_pem": csr_pem.decode("utf-8"),
        "cuit": clean_cuit,
        "razon_social": razon_clean,
        "alias": alias_clean,
        "subject": subject.rfc4514_string(),
    }


def _extract_cert_metadata(cert: x509.Certificate) -> dict[str, Any]:
    """Extrae metadatos estándar de un certificado X.509."""
    now_utc = datetime.now(timezone.utc)
    emision_utc = cert.not_valid_before_utc
    vencimiento_utc = cert.not_valid_after_utc

    if now_utc >= vencimiento_utc:
        dias_restantes = min(-1, (vencimiento_utc.date() - now_utc.date()).days)
    else:
        dias_restantes = (vencimiento_utc.date() - now_utc.date()).days

    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": str(cert.serial_number),
        "fecha_emision": emision_utc.isoformat(),
        "fecha_vencimiento": vencimiento_utc.isoformat(),
        "dias_restantes": dias_restantes,
    }


def guardar_y_validar_certificado(
    crt_bytes: bytes | str,
    key_bytes: bytes | str | None = None,
) -> dict[str, Any]:
    """
    Verifica que crt_bytes sea un certificado X.509 PEM válido, comprueba
    matemáticamente que su clave pública coincida con la clave privada (arca.key
    nueva o existente), guarda el certificado (y clave si se provee) y extrae
    sus metadatos.
    """
    if not crt_bytes:
        raise ValueError("El certificado proporcionado está vacío.")

    if isinstance(crt_bytes, str):
        crt_raw = crt_bytes.encode("utf-8")
    elif isinstance(crt_bytes, (bytes, bytearray)):
        crt_raw = bytes(crt_bytes)
    else:
        raise ValueError("El certificado debe proporcionarse en formato bytes o string PEM.")

    try:
        cert = x509.load_pem_x509_certificate(crt_raw)
    except Exception as exc:
        raise ValueError("El archivo proporcionado no es un certificado X.509 PEM válido.") from exc

    _ensure_arca_dir()

    if key_bytes is not None:
        if isinstance(key_bytes, str):
            key_raw = key_bytes.encode("utf-8")
        elif isinstance(key_bytes, (bytes, bytearray)):
            key_raw = bytes(key_bytes)
        else:
            raise ValueError("La clave privada debe proporcionarse en formato bytes o string PEM.")

        try:
            private_key = serialization.load_pem_private_key(key_raw, password=None)
        except Exception as exc:
            raise ValueError(
                "La clave privada proporcionada no tiene un formato PEM válido o requiere contraseña."
            ) from exc
    else:
        if not ARCA_KEY_PATH.exists():
            raise ValueError(
                "No se encontró una clave privada local (arca.key) ni se proporcionó una nueva."
            )
        try:
            key_raw = ARCA_KEY_PATH.read_bytes()
            private_key = serialization.load_pem_private_key(key_raw, password=None)
        except Exception as exc:
            raise ValueError("La clave privada existente (arca.key) no es un archivo PEM válido.") from exc

    # Verificación matemática de correspondencia entre clave pública del certificado y clave privada
    cert_pub_numbers = cert.public_key().public_numbers()
    key_pub_numbers = private_key.public_key().public_numbers()
    if cert_pub_numbers != key_pub_numbers:
        raise ValueError(
            "El certificado X.509 no coincide matemáticamente con la clave privada (arca.key)."
        )

    if key_bytes is not None:
        ARCA_KEY_PATH.write_bytes(key_raw)

    ARCA_CRT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return _extract_cert_metadata(cert)


def get_certificate_status() -> dict[str, Any]:
    """
    Retorna el estado actual del certificado ("VIGENTE", "PROXIMO_A_VENCER",
    "VENCIDO", "SIN_CERTIFICADO") y establece alerta_vencimiento = True cuando
    dias_restantes <= dias_alerta_vencimiento.
    """
    config = get_arca_config()
    dias_alerta = int(config.get("dias_alerta_vencimiento", DEFAULT_DIAS_ALERTA_VENCIMIENTO))

    if not ARCA_CRT_PATH.exists():
        return {
            "status": "SIN_CERTIFICADO",
            "estado": "SIN_CERTIFICADO",
            "alerta_vencimiento": False,
            "dias_restantes": None,
            "dias_alerta_vencimiento": dias_alerta,
            "has_private_key": ARCA_KEY_PATH.exists(),
            "has_csr": ARCA_CSR_PATH.exists(),
            "has_certificate": False,
            "subject": None,
            "issuer": None,
            "serial_number": None,
            "fecha_emision": None,
            "fecha_vencimiento": None,
        }

    try:
        cert = x509.load_pem_x509_certificate(ARCA_CRT_PATH.read_bytes())
    except Exception as exc:
        raise ValueError("El certificado almacenado (arca.crt) tiene un formato PEM inválido.") from exc

    meta = _extract_cert_metadata(cert)
    dias_restantes = meta["dias_restantes"]
    alerta_vencimiento = bool(dias_restantes <= dias_alerta)

    if dias_restantes < 0:
        estado = "VENCIDO"
    elif dias_restantes <= dias_alerta:
        estado = "PROXIMO_A_VENCER"
    else:
        estado = "VIGENTE"

    return {
        "status": estado,
        "estado": estado,
        "alerta_vencimiento": alerta_vencimiento,
        "dias_alerta_vencimiento": dias_alerta,
        "has_private_key": ARCA_KEY_PATH.exists(),
        "has_csr": ARCA_CSR_PATH.exists(),
        "has_certificate": True,
        **meta,
    }


# ==============================================================================
# ETAPA 2: Integración SOAP WSAA (LoginCms) y WSFEv1
# ==============================================================================


def generar_login_ticket_request(service: str = "wsfe") -> str:
    """
    Genera el documento XML loginTicketRequest (TRA) requerido por WSAA.
    """
    now_utc = datetime.now(timezone.utc)
    gen_time = (now_utc - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    exp_time = (now_utc + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    unique_id = int(now_utc.timestamp())

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<loginTicketRequest version="1.0">\n'
        "  <header>\n"
        f"    <uniqueId>{unique_id}</uniqueId>\n"
        f"    <generationTime>{gen_time}</generationTime>\n"
        f"    <expirationTime>{exp_time}</expirationTime>\n"
        "  </header>\n"
        f"  <service>{service}</service>\n"
        "</loginTicketRequest>"
    )


def firmar_tra_cms(tra_xml: str | bytes) -> str:
    """
    Firma el XML loginTicketRequest mediante PKCS7SignatureBuilder (CMS DER)
    usando el certificado (arca.crt) y clave privada (arca.key) locales, y
    retorna el CMS codificado en Base64 listo para enviar a LoginCms.
    """
    if not ARCA_CRT_PATH.exists() or not ARCA_KEY_PATH.exists():
        raise ValueError(
            "Faltan los archivos de certificado (arca.crt) o clave privada (arca.key) en data/certs/arca/."
        )

    cert = x509.load_pem_x509_certificate(ARCA_CRT_PATH.read_bytes())
    private_key = serialization.load_pem_private_key(ARCA_KEY_PATH.read_bytes(), password=None)

    tra_bytes = tra_xml.encode("utf-8") if isinstance(tra_xml, str) else bytes(tra_xml)

    cms_der = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra_bytes)
        .add_signer(cert, private_key, hashes.SHA256())
        .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
    )
    return base64.b64encode(cms_der).decode("ascii")


def _load_cached_ta(environment: str, service: str = "wsfe") -> dict[str, Any] | None:
    """
    Lee el Ticket de Acceso (Token y Sign) desde la caché local en data/certs/arca/
    si existe y aún se encuentra vigente.
    """
    if not ARCA_TA_CACHE_PATH.exists():
        return None

    try:
        cache_data = json.loads(ARCA_TA_CACHE_PATH.read_text(encoding="utf-8"))
        key = f"{environment}:{service}"
        entry = cache_data.get(key)
        if not isinstance(entry, dict):
            return None

        token = entry.get("token")
        sign = entry.get("sign")
        exp_str = entry.get("expiration_time")
        if not token or not sign or not exp_str:
            return None

        exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)

        # Margen de seguridad de 2 minutos antes del vencimiento
        if datetime.now(timezone.utc) + timedelta(minutes=2) < exp_dt:
            return {
                "token": token,
                "sign": sign,
                "expiration_time": exp_str,
                "environment": environment,
                "service": service,
            }
    except Exception as exc:
        logger.warning(f"No se pudo reutilizar caché local de TA: {exc}")

    return None


def _save_cached_ta(
    environment: str,
    service: str,
    token: str,
    sign: str,
    expiration_time: str,
) -> None:
    """Guarda el Ticket de Acceso (Token y Sign) en data/certs/arca/arca_ta_cache.json."""
    _ensure_arca_dir()
    cache_data: dict[str, Any] = {}
    if ARCA_TA_CACHE_PATH.exists():
        try:
            loaded = json.loads(ARCA_TA_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cache_data = loaded
        except Exception:
            cache_data = {}

    key = f"{environment}:{service}"
    cache_data[key] = {
        "token": token,
        "sign": sign,
        "expiration_time": expiration_time,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    ARCA_TA_CACHE_PATH.write_text(
        json.dumps(cache_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _strip_ns(tag: str) -> str:
    """Elimina el namespace XML de un tag ElementTree."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _find_text_local(root: ET.Element, local_name: str) -> str | None:
    """Busca recursivamente el primer elemento cuyo nombre local coincida y retorna su texto."""
    for elem in root.iter():
        if _strip_ns(elem.tag) == local_name and elem.text is not None:
            return elem.text.strip()
    return None


def login_cms_wsaa(environment: str, service: str = "wsfe") -> dict[str, Any]:
    """
    Obtiene un Ticket de Acceso (Token y Sign) para el servicio especificado.
    - Si environment == "mock", no realiza ninguna conexión saliente y retorna valores simulados.
    - Si existe un TA vigente en caché local (data/certs/arca/), lo reutiliza.
    - En caso contrario, firma el loginTicketRequest y llama por SOAP a LoginCms.
    """
    env_clean = str(environment or "mock").strip().lower()
    if env_clean == "mock":
        return {
            "token": "MOCK_TOKEN_ARCA",
            "sign": "MOCK_SIGN_ARCA",
            "expiration_time": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
            "environment": "mock",
            "service": service,
        }

    if env_clean not in WSAA_URLS:
        raise ValueError(f"Entorno WSAA inválido: {environment}")

    cached = _load_cached_ta(env_clean, service)
    if cached:
        return cached

    tra_xml = generar_login_ticket_request(service=service)
    cms_b64 = firmar_tra_cms(tra_xml)

    soap_envelope = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        "<wsaa:loginCms>"
        f"<wsaa:in0>{cms_b64}</wsaa:in0>"
        "</wsaa:loginCms>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )

    wsaa_url = WSAA_URLS[env_clean]
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '""',
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(wsaa_url, content=soap_envelope.encode("utf-8"), headers=headers)

    root = ET.fromstring(response.text)
    fault_string = _find_text_local(root, "faultstring")
    if fault_string:
        raise ValueError(f"Error SOAP WSAA ({env_clean}): {fault_string}")

    login_return = _find_text_local(root, "loginCmsReturn")
    if not login_return:
        raise ValueError("Respuesta inválida de WSAA: no se encontró loginCmsReturn.")

    ta_root = ET.fromstring(html.unescape(login_return))
    token = _find_text_local(ta_root, "token")
    sign = _find_text_local(ta_root, "sign")
    exp_time = _find_text_local(ta_root, "expirationTime") or (
        datetime.now(timezone.utc) + timedelta(hours=12)
    ).isoformat()

    if not token or not sign:
        raise ValueError("WSAA no devolvió Token o Sign válidos.")

    _save_cached_ta(env_clean, service, token, sign, exp_time)

    return {
        "token": token,
        "sign": sign,
        "expiration_time": exp_time,
        "environment": env_clean,
        "service": service,
    }


def _call_wsfev1_soap(environment: str, action: str, body_inner_xml: str) -> ET.Element:
    """
    Envía una petición SOAP al servicio WSFEv1 en homologación o producción.
    Prohibido invocar en modo mock.
    """
    env_clean = str(environment or "mock").strip().lower()
    if env_clean == "mock":
        raise RuntimeError("No se permiten llamadas SOAP salientes cuando el entorno es 'mock'.")

    if env_clean not in WSFEV1_URLS:
        raise ValueError(f"Entorno WSFEv1 inválido: {environment}")

    soap_envelope = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Header/>"
        "<soap:Body>"
        f"{body_inner_xml}"
        "</soap:Body>"
        "</soap:Envelope>"
    )

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{FEV1_NS}{action}"',
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            WSFEV1_URLS[env_clean],
            content=soap_envelope.encode("utf-8"),
            headers=headers,
        )

    root = ET.fromstring(response.text)
    fault_string = _find_text_local(root, "faultstring")
    if fault_string:
        raise ValueError(f"Error SOAP WSFEv1 ({action}): {fault_string}")

    # Verificar bloque <Errors> de WSFEv1
    errors_msgs: list[str] = []
    for elem in root.iter():
        if _strip_ns(elem.tag) == "Err":
            code = _find_text_local(elem, "Code") or ""
            msg = _find_text_local(elem, "Msg") or ""
            errors_msgs.append(f"[{code}] {msg}".strip())
    if errors_msgs:
        raise ValueError(f"Error WSFEv1 ({action}): {'; '.join(errors_msgs)}")

    return root


class ArcaService:
    """
    Servicio de integración con ARCA/AFIP (WSAA y WSFEv1).
    Soporta todos los tipos de comprobantes electrónicos (Facturas A/B/C/M/E,
    Notas de Débito/Crédito, Recibos y Facturas de Crédito Electrónicas MiPyMEs),
    así como la gestión local de certificados digitales X.509 y configuración.
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

    @staticmethod
    def get_arca_config() -> dict[str, Any]:
        return get_arca_config()

    @staticmethod
    def save_arca_config(data: dict[str, Any]) -> dict[str, Any]:
        return save_arca_config(data)

    @staticmethod
    def generar_key_y_csr(cuit: str | int, razon_social: str, alias: str) -> dict[str, Any]:
        return generar_key_y_csr(cuit, razon_social, alias)

    @staticmethod
    def guardar_y_validar_certificado(
        crt_bytes: bytes | str,
        key_bytes: bytes | str | None = None,
    ) -> dict[str, Any]:
        return guardar_y_validar_certificado(crt_bytes, key_bytes=key_bytes)

    @staticmethod
    def get_certificate_status() -> dict[str, Any]:
        return get_certificate_status()

    def obtener_ticket_acceso(self, service: str = "wsfe") -> dict[str, Any]:
        """Obtiene (o recupera de caché) el Ticket de Acceso WSAA (Token y Sign)."""
        if self.use_mock or self.environment == "mock":
            return login_cms_wsaa("mock", service=service)
        return login_cms_wsaa(self.environment, service=service)

    def fe_dummy(self) -> dict[str, Any]:
        """
        Verifica el estado de los servidores de ARCA (FEDummy: AppServer, DbServer, AuthServer).
        En modo mock retorna estado OK simulado sin realizar llamadas de red.
        """
        if self.use_mock or self.environment == "mock":
            return {
                "AppServer": "OK",
                "DbServer": "OK",
                "AuthServer": "OK",
                "environment": "mock",
                "ok": True,
            }

        body_xml = f'<FEDummy xmlns="{FEV1_NS}" />'
        root = _call_wsfev1_soap(self.environment, "FEDummy", body_xml)
        app_srv = _find_text_local(root, "AppServer") or "ERROR"
        db_srv = _find_text_local(root, "DbServer") or "ERROR"
        auth_srv = _find_text_local(root, "AuthServer") or "ERROR"

        return {
            "AppServer": app_srv,
            "DbServer": db_srv,
            "AuthServer": auth_srv,
            "environment": self.environment,
            "ok": app_srv == "OK" and db_srv == "OK" and auth_srv == "OK",
        }

    # Alias con nombre exacto del método SOAP
    FEDummy = fe_dummy

    def fe_comp_ultimo_autorizado(
        self,
        punto_venta: int,
        tipo_comprobante: int,
        db=None,
    ) -> int:
        """
        Consulta el último número de comprobante autorizado en ARCA (FECompUltimoAutorizado).
        En modo mock consulta la base de datos local sin abrir conexiones externas.
        """
        if self.use_mock or self.environment == "mock":
            if db is not None:
                from src.database.models.creditos.facturacion import Factura

                max_nro = (
                    db.query(func.max(Factura.nro_comprobante))
                    .filter(
                        Factura.punto_venta == int(punto_venta),
                        Factura.tipo_comprobante == int(tipo_comprobante),
                    )
                    .scalar()
                )
                return int(max_nro or 0)
            return 0

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)

        body_xml = (
            f'<FECompUltimoAutorizado xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            f"<PtoVta>{int(punto_venta)}</PtoVta>"
            f"<CbteTipo>{int(tipo_comprobante)}</CbteTipo>"
            "</FECompUltimoAutorizado>"
        )

        root = _call_wsfev1_soap(self.environment, "FECompUltimoAutorizado", body_xml)
        cbte_nro_str = _find_text_local(root, "CbteNro")
        return int(cbte_nro_str or 0)

    # Alias con nombre exacto del método SOAP
    FECompUltimoAutorizado = fe_comp_ultimo_autorizado

    def obtener_proximo_numero(self, db, punto_venta: int, tipo_comprobante: int) -> int:
        if self.use_mock or self.environment == "mock":
            from src.database.models.creditos.facturacion import Factura

            max_nro = (
                db.query(func.max(Factura.nro_comprobante))
                .filter(
                    Factura.punto_venta == int(punto_venta),
                    Factura.tipo_comprobante == int(tipo_comprobante),
                )
                .scalar()
            )
            return int(max_nro or 0) + 1

        ultimo = self.fe_comp_ultimo_autorizado(punto_venta, tipo_comprobante, db=db)
        return int(ultimo) + 1

    def fe_cae_solicitar(
        self,
        punto_venta: int,
        tipo_comprobante: int,
        nro_comprobante: int,
        importe_total: float,
        cuit_cliente: str | None = None,
        fecha_emision: date | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Solicita la autorización de un comprobante electrónico mediante el método
        SOAP FECAESolicitar de WSFEv1.
        """
        fecha_eff = fecha_emision or datetime.now().date()
        if self.use_mock or self.environment == "mock":
            cae = f"7{random.randint(1000000000000, 9999999999999)}"
            vencimiento_cae = fecha_eff + timedelta(days=10)
            return {
                "nro_comprobante": int(nro_comprobante),
                "cae": cae,
                "vencimiento_cae": vencimiento_cae,
                "fecha_emision": fecha_eff,
                "importe_total": round(float(importe_total), 2),
                "punto_venta": int(punto_venta),
                "tipo_comprobante": int(tipo_comprobante),
                "cuit_cliente": cuit_cliente,
            }

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)

        concepto = int(kwargs.get("concepto_arca", 2))
        clean_doc = _clean_cuit(cuit_cliente)
        tipo_doc_str = str(kwargs.get("tipo_doc_receptor", "")).upper().strip()
        if clean_doc and len(clean_doc) == 11:
            doc_tipo = 86 if tipo_doc_str == "CUIL" else 80
            doc_nro = int(clean_doc)
        elif clean_doc and len(clean_doc) >= 7:
            doc_tipo = 96  # DNI
            doc_nro = int(clean_doc)
        else:
            doc_tipo = 99  # Consumidor Final
            doc_nro = 0

        imp_total = round(float(importe_total), 2)
        imp_no_gravado = round(float(kwargs.get("importe_no_gravado", 0.0) or 0.0), 2)
        imp_exento = round(float(kwargs.get("importe_exento", 0.0) or 0.0), 2)
        neto_21 = round(float(kwargs.get("neto_gravado_21", 0.0) or 0.0), 2)
        neto_105 = round(float(kwargs.get("neto_gravado_105", 0.0) or 0.0), 2)
        neto_27 = round(float(kwargs.get("neto_gravado_27", 0.0) or 0.0), 2)
        iva_21 = round(float(kwargs.get("iva_21", 0.0) or 0.0), 2)
        iva_105 = round(float(kwargs.get("iva_105", 0.0) or 0.0), 2)
        iva_27 = round(float(kwargs.get("iva_27", 0.0) or 0.0), 2)
        imp_trib = round(float(kwargs.get("otros_tributos", 0.0) or 0.0), 2)

        imp_neto = round(neto_21 + neto_105 + neto_27, 2)
        imp_iva = round(iva_21 + iva_105 + iva_27, 2)

        # Si no se pasó desglose explícito, inferir de importe_total
        if (imp_no_gravado + imp_exento + imp_neto + imp_iva + imp_trib) == 0.0 and imp_total > 0:
            if int(tipo_comprobante) in (11, 12, 13, 15, 19, 20, 21, 211, 212, 213):
                imp_neto = imp_total
            else:
                imp_neto = round(imp_total / 1.21, 2)
                imp_iva = round(imp_total - imp_neto, 2)
                neto_21 = imp_neto
                iva_21 = imp_iva

        cbte_fch = fecha_eff.strftime("%Y%m%d")
        serv_xml = ""
        if concepto in (2, 3):
            f_desde = kwargs.get("fecha_servicio_desde") or fecha_eff
            f_hasta = kwargs.get("fecha_servicio_hasta") or fecha_eff
            f_vto = kwargs.get("fecha_vencimiento_pago") or fecha_eff
            serv_xml = (
                f"<FchServDesde>{f_desde.strftime('%Y%m%d')}</FchServDesde>"
                f"<FchServHasta>{f_hasta.strftime('%Y%m%d')}</FchServHasta>"
                f"<FchVtoPago>{f_vto.strftime('%Y%m%d')}</FchVtoPago>"
            )

        iva_items_xml = ""
        if imp_iva > 0:
            alic_list: list[str] = []
            if neto_21 > 0 or iva_21 > 0:
                alic_list.append(
                    f"<AlicIva><Id>5</Id><BaseImp>{neto_21:.2f}</BaseImp><Importe>{iva_21:.2f}</Importe></AlicIva>"
                )
            if neto_105 > 0 or iva_105 > 0:
                alic_list.append(
                    f"<AlicIva><Id>4</Id><BaseImp>{neto_105:.2f}</BaseImp><Importe>{iva_105:.2f}</Importe></AlicIva>"
                )
            if neto_27 > 0 or iva_27 > 0:
                alic_list.append(
                    f"<AlicIva><Id>6</Id><BaseImp>{neto_27:.2f}</BaseImp><Importe>{iva_27:.2f}</Importe></AlicIva>"
                )
            if alic_list:
                iva_items_xml = f"<Iva>{''.join(alic_list)}</Iva>"

        body_xml = (
            f'<FECAESolicitar xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            "<FeCAEReq>"
            "<FeCabReq>"
            "<CantReg>1</CantReg>"
            f"<PtoVta>{int(punto_venta)}</PtoVta>"
            f"<CbteTipo>{int(tipo_comprobante)}</CbteTipo>"
            "</FeCabReq>"
            "<FeDetReq>"
            "<FECAEDetRequest>"
            f"<Concepto>{concepto}</Concepto>"
            f"<DocTipo>{doc_tipo}</DocTipo>"
            f"<DocNro>{doc_nro}</DocNro>"
            f"<CbteDesde>{int(nro_comprobante)}</CbteDesde>"
            f"<CbteHasta>{int(nro_comprobante)}</CbteHasta>"
            f"<CbteFch>{cbte_fch}</CbteFch>"
            f"<ImpTotal>{imp_total:.2f}</ImpTotal>"
            f"<ImpTotConc>{imp_no_gravado:.2f}</ImpTotConc>"
            f"<ImpNeto>{imp_neto:.2f}</ImpNeto>"
            f"<ImpOpEx>{imp_exento:.2f}</ImpOpEx>"
            f"<ImpTrib>{imp_trib:.2f}</ImpTrib>"
            f"<ImpIVA>{imp_iva:.2f}</ImpIVA>"
            f"{serv_xml}"
            "<MonId>PES</MonId>"
            "<MonCotiz>1</MonCotiz>"
            f"{iva_items_xml}"
            "</FECAEDetRequest>"
            "</FeDetReq>"
            "</FeCAEReq>"
            "</FECAESolicitar>"
        )

        root = _call_wsfev1_soap(self.environment, "FECAESolicitar", body_xml)
        resultado = _find_text_local(root, "Resultado")
        cae = _find_text_local(root, "CAE")
        cae_vto_str = _find_text_local(root, "CAEFchVto")

        if resultado != "A" or not cae:
            obs_msgs: list[str] = []
            for elem in root.iter():
                if _strip_ns(elem.tag) == "Obs":
                    code = _find_text_local(elem, "Code") or ""
                    msg = _find_text_local(elem, "Msg") or ""
                    obs_msgs.append(f"[{code}] {msg}".strip())
            detalle = "; ".join(obs_msgs) if obs_msgs else "Comprobante rechazado sin CAE."
            raise ValueError(f"ARCA rechazó el comprobante ({resultado}): {detalle}")

        if cae_vto_str and len(cae_vto_str) == 8 and cae_vto_str.isdigit():
            vencimiento_cae = datetime.strptime(cae_vto_str, "%Y%m%d").date()
        else:
            vencimiento_cae = fecha_eff + timedelta(days=10)

        return {
            "nro_comprobante": int(nro_comprobante),
            "cae": cae,
            "vencimiento_cae": vencimiento_cae,
            "fecha_emision": fecha_eff,
            "importe_total": imp_total,
            "punto_venta": int(punto_venta),
            "tipo_comprobante": int(tipo_comprobante),
            "cuit_cliente": cuit_cliente,
        }

    # Alias con nombre exacto del método SOAP
    FECAESolicitar = fe_cae_solicitar

    def emitir_factura(
        self,
        punto_venta: int,
        tipo_comprobante: int,
        importe_total: float,
        cuit_cliente: str | None = None,
        fecha_emision: date | None = None,
        ultimo_nro: int | None = None,
        db=None,
        **kwargs,
    ) -> dict:
        """
        Emite un comprobante electrónico en ARCA y retorna el número correlativo,
        CAE y fecha de vencimiento de CAE.
        En modo mock mantiene el comportamiento simulado sin llamadas de red.
        En homologación o producción utiliza FECompUltimoAutorizado y FECAESolicitar.
        """
        fecha_eff = fecha_emision or datetime.now().date()
        if self.use_mock or self.environment == "mock":
            if ultimo_nro is not None:
                nro_comprobante = int(ultimo_nro) + 1
            elif db is not None:
                nro_comprobante = self.obtener_proximo_numero(db, punto_venta, tipo_comprobante)
            else:
                nro_comprobante = random.randint(1000, 9999)

            logger.info(
                f"[ARCA MOCK] Emitiendo comprobante Tipo {tipo_comprobante} "
                f"PV {punto_venta:04d}-{nro_comprobante:08d} por ${float(importe_total):,.2f}"
            )

            cae = f"7{random.randint(1000000000000, 9999999999999)}"
            vencimiento_cae = fecha_eff + timedelta(days=10)

            return {
                "nro_comprobante": nro_comprobante,
                "cae": cae,
                "vencimiento_cae": vencimiento_cae,
                "fecha_emision": fecha_eff,
                "importe_total": round(float(importe_total), 2),
                "punto_venta": int(punto_venta),
                "tipo_comprobante": int(tipo_comprobante),
                "cuit_cliente": cuit_cliente,
            }

        if ultimo_nro is not None:
            nro_comprobante = int(ultimo_nro) + 1
        else:
            nro_comprobante = self.obtener_proximo_numero(db, punto_venta, tipo_comprobante)

        return self.fe_cae_solicitar(
            punto_venta=punto_venta,
            tipo_comprobante=tipo_comprobante,
            nro_comprobante=nro_comprobante,
            importe_total=importe_total,
            cuit_cliente=cuit_cliente,
            fecha_emision=fecha_eff,
            **kwargs,
        )
