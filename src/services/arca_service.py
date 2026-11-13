import base64
import contextlib
import html
import json
import logging
import os
import random
import re
import threading
import time
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

CONDICIONES_IVA_EMISOR_VALIDAS = ("RESPONSABLE_INSCRIPTO", "MONOTRIBUTISTA", "EXENTO")
FCE_SISTEMAS_CIRCULACION = ("ADC", "SCA")

CODIGOS_CLASE_A = {1, 2, 3, 4, 5, 201, 202, 203}
CODIGOS_CLASE_B = {6, 7, 8, 9, 206, 207, 208}
CODIGOS_CLASE_C = {11, 12, 13, 15, 211, 212, 213}
CODIGOS_CLASE_E = {19, 20, 21}
CODIGOS_CLASE_M = {51, 52, 53, 54}
CODIGOS_NOTA_CREDITO_DEBITO = {2, 3, 7, 8, 12, 13, 20, 21, 52, 53, 202, 203, 207, 208, 212, 213}
CODIGOS_FCE_FACTURA = {201, 206, 211}
CODIGOS_FCE_NOTA = {202, 203, 207, 208, 212, 213}

# Catálogo oficial RG 5616 / FEParamGetCondicionIvaReceptor
CONDICIONES_IVA_RECEPTOR_CATALOGO: list[dict[str, Any]] = [
    {
        "id": 1,
        "codigo": "RESPONSABLE INSCRIPTO",
        "descripcion": "IVA Responsable Inscripto",
        "clases_permitidas": ["A", "M", "C"],
    },
    {
        "id": 4,
        "codigo": "EXENTO",
        "descripcion": "IVA Sujeto Exento",
        "clases_permitidas": ["B", "C"],
    },
    {
        "id": 5,
        "codigo": "CONSUMIDOR FINAL",
        "descripcion": "Consumidor Final",
        "clases_permitidas": ["B", "C"],
    },
    {
        "id": 6,
        "codigo": "MONOTRIBUTISTA",
        "descripcion": "Responsable Monotributo",
        "clases_permitidas": ["A", "M", "B", "C"],
    },
    {
        "id": 7,
        "codigo": "SUJETO NO CATEGORIZADO",
        "descripcion": "Sujeto No Categorizado",
        "clases_permitidas": ["B", "C"],
    },
    {
        "id": 8,
        "codigo": "PROVEEDOR DEL EXTERIOR",
        "descripcion": "Proveedor del Exterior",
        "clases_permitidas": ["B", "C", "E"],
    },
    {
        "id": 9,
        "codigo": "CLIENTE DEL EXTERIOR",
        "descripcion": "Cliente del Exterior",
        "clases_permitidas": ["B", "C", "E"],
    },
    {
        "id": 10,
        "codigo": "IVA LIBERADO",
        "descripcion": "IVA Liberado - Ley Nº 19.640",
        "clases_permitidas": ["B", "C"],
    },
    {
        "id": 13,
        "codigo": "MONOTRIBUTISTA SOCIAL",
        "descripcion": "Monotributista Social",
        "clases_permitidas": ["A", "M", "B", "C"],
    },
    {
        "id": 15,
        "codigo": "IVA NO ALCANZADO",
        "descripcion": "IVA No Alcanzado",
        "clases_permitidas": ["B", "C"],
    },
    {
        "id": 16,
        "codigo": "MONOTRIBUTO PROMOVIDO",
        "descripcion": "Monotributo Trabajador Independiente Promovido",
        "clases_permitidas": ["A", "M", "B", "C"],
    },
]

CONDICION_IVA_RECEPTOR_MAP: dict[str, int] = {
    "1": 1,
    "RI": 1,
    "RESPONSABLE INSCRIPTO": 1,
    "RESPONSABLE_INSCRIPTO": 1,
    "IVA RESPONSABLE INSCRIPTO": 1,
    "4": 4,
    "EXENTO": 4,
    "SUJETO EXENTO": 4,
    "IVA SUJETO EXENTO": 4,
    "5": 5,
    "CF": 5,
    "CONSUMIDOR FINAL": 5,
    "CONSUMIDOR_FINAL": 5,
    "6": 6,
    "MONOTRIBUTO": 6,
    "MONOTRIBUTISTA": 6,
    "RESPONSABLE MONOTRIBUTO": 6,
    "7": 7,
    "SUJETO NO CATEGORIZADO": 7,
    "NO CATEGORIZADO": 7,
    "8": 8,
    "PROVEEDOR DEL EXTERIOR": 8,
    "9": 9,
    "CLIENTE DEL EXTERIOR": 9,
    "10": 10,
    "IVA LIBERADO": 10,
    "IVA LIBERADO - LEY Nº 19.640": 10,
    "13": 13,
    "MONOTRIBUTISTA SOCIAL": 13,
    "15": 15,
    "IVA NO ALCANZADO": 15,
    "IVA_NO_ALCANZADO": 15,
    "NO ALCANZADO": 15,
    "ORGANISMO ESTATAL": 15,
    "ESTATAL": 15,
    "16": 16,
    "MONOTRIBUTO PROMOVIDO": 16,
    "MONOTRIBUTO TRABAJADOR INDEPENDIENTE PROMOVIDO": 16,
}

# Catálogo oficial FEParamGetTiposTributos
TIPOS_TRIBUTO_CATALOGO: list[dict[str, Any]] = [
    {"id": 1, "descripcion": "Impuestos nacionales"},
    {"id": 2, "descripcion": "Impuestos provinciales"},
    {"id": 3, "descripcion": "Impuestos municipales"},
    {"id": 4, "descripcion": "Impuestos Internos"},
    {"id": 99, "descripcion": "Otro"},
]

WSAA_URLS = {
    "homologacion": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
    "produccion": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
}

WSFEV1_URLS = {
    "homologacion": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
    "produccion": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
}

FEV1_NS = "http://ar.gov.afip.dif.FEV1/"

_GLOBAL_LOCK_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCAL_HELD = threading.local()


class ArcaServiceError(ValueError):
    """Excepción estructurada para errores de validación o comunicación con ARCA/AFIP."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_http: int = 400,
        observations: list[str] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.status_http = status_http
        self.observations = observations or []


def _ensure_arca_dir() -> Path:
    """Crea el directorio local data/certs/arca/ si no existe."""
    ARCA_CERTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARCA_CERTS_DIR


@contextlib.contextmanager
def _arca_lock(lock_name: str, timeout: float = 30.0):
    """
    Lock híbrido (thread RLock + archivo de sistema operativo) para serializar
    acceso a caché de TA y numeración correlativa entre múltiples workers (ej. Gunicorn).
    Reentrante dentro del mismo hilo sin volver a bloquear el descriptor de archivo OS.
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", lock_name)
    held: set[str] = getattr(_THREAD_LOCAL_HELD, "locks", None)
    if held is None:
        held = set()
        _THREAD_LOCAL_HELD.locks = held

    if safe_name in held:
        yield
        return

    with _GLOBAL_LOCK_GUARD:
        t_lock = _THREAD_LOCKS.get(safe_name)
        if t_lock is None:
            t_lock = threading.RLock()
            _THREAD_LOCKS[safe_name] = t_lock

    with t_lock:
        held.add(safe_name)
        locks_dir = _ensure_arca_dir() / ".locks"
        locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file_path = locks_dir / f"{safe_name}.lock"
        fh = open(lock_file_path, "a+b")
        locked_os = False
        try:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                fh.write(b"0")
                fh.flush()
            fh.seek(0)
            deadline = time.monotonic() + timeout
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked_os = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        logger.warning(f"Timeout esperando lock de archivo ARCA '{safe_name}'")
                        break
                    time.sleep(0.05)
            yield
        finally:
            held.discard(safe_name)
            if locked_os:
                try:
                    fh.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            try:
                fh.close()
            except OSError:
                pass


def _clean_cuit(cuit: str | int | None) -> str:
    """Limpia guiones o espacios y retorna solo los dígitos del CUIT."""
    if cuit is None:
        return ""
    return "".join(filter(str.isdigit, str(cuit)))


def normalize_condicion_iva_emisor(val: str | None) -> str:
    """Normaliza la condición frente al IVA del emisor."""
    if not val:
        return "RESPONSABLE_INSCRIPTO"
    clean = str(val).strip().upper().replace(" ", "_")
    if clean in ("MONOTRIBUTO", "MONOTRIBUTISTA", "RESPONSABLE_MONOTRIBUTO"):
        return "MONOTRIBUTISTA"
    if clean in ("EXENTO", "IVA_SUJETO_EXENTO", "SUJETO_EXENTO"):
        return "EXENTO"
    if clean in ("RESPONSABLE_INSCRIPTO", "IVA_RESPONSABLE_INSCRIPTO", "RI"):
        return "RESPONSABLE_INSCRIPTO"
    return "RESPONSABLE_INSCRIPTO"


def format_condicion_iva_emisor(val: str | None) -> str:
    """Devuelve la etiqueta legible para PDF y UI de la condición IVA del emisor."""
    norm = normalize_condicion_iva_emisor(val)
    if norm == "MONOTRIBUTISTA":
        return "Responsable Monotributo"
    if norm == "EXENTO":
        return "IVA Sujeto Exento"
    return "IVA Responsable Inscripto"


def resolve_condicion_iva_receptor_id(
    condicion_iva_receptor: str | int | None,
    tipo_comprobante: int | None = None,
    doc_tipo: int = 99,
) -> int:
    """
    Resuelve el código numérico de CondicionIVAReceptorId exigido por RG 5616/2024.
    """
    if isinstance(condicion_iva_receptor, int) and condicion_iva_receptor in {
        item["id"] for item in CONDICIONES_IVA_RECEPTOR_CATALOGO
    }:
        return condicion_iva_receptor

    if condicion_iva_receptor is not None:
        raw_str = str(condicion_iva_receptor).strip().upper()
        if raw_str in CONDICION_IVA_RECEPTOR_MAP:
            return CONDICION_IVA_RECEPTOR_MAP[raw_str]
        for key, code_id in CONDICION_IVA_RECEPTOR_MAP.items():
            if len(key) > 2 and key in raw_str:
                return code_id

    cbte = int(tipo_comprobante or 6)
    if cbte in CODIGOS_CLASE_A or cbte in CODIGOS_CLASE_M:
        return 1  # IVA Responsable Inscripto
    if cbte in CODIGOS_CLASE_E:
        return 9  # Cliente del Exterior
    if doc_tipo == 80 and cbte in CODIGOS_CLASE_C:
        return 1
    return 5  # Consumidor Final


def get_arca_config() -> dict[str, Any]:
    """
    Lee la configuración local de ARCA desde data/certs/arca/arca_config.json.
    Si no existe, crea el directorio y retorna la configuración por defecto.
    """
    _ensure_arca_dir()
    default_cuit = _clean_cuit(COMPANY_DATA.cuit) or "30000000000"
    default_config: dict[str, Any] = {
        "environment": "mock",
        "cuit": default_cuit,
        "punto_venta_default": 1,
        "dias_alerta_vencimiento": DEFAULT_DIAS_ALERTA_VENCIMIENTO,
        "condicion_iva_emisor": "RESPONSABLE_INSCRIPTO",
        "condicion_iva_emisor_label": "IVA Responsable Inscripto",
        "nro_iibb": default_cuit,
        "inicio_actividades": "01/01/2020",
        "cbu_fce_default": "",
        "fce_sistema_circulacion": "ADC",
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

    cuit_val = _clean_cuit(raw.get("cuit", default_config["cuit"])) or default_cuit
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

    cond_emisor = normalize_condicion_iva_emisor(
        raw.get("condicion_iva_emisor", default_config["condicion_iva_emisor"])
    )
    nro_iibb = str(raw.get("nro_iibb") if raw.get("nro_iibb") is not None else cuit_val).strip()
    inicio_act = str(
        raw.get("inicio_actividades") or default_config["inicio_actividades"]
    ).strip()
    cbu_fce = _clean_cuit(raw.get("cbu_fce_default", ""))
    fce_sist = str(raw.get("fce_sistema_circulacion", "ADC") or "ADC").strip().upper()
    if fce_sist not in FCE_SISTEMAS_CIRCULACION:
        fce_sist = "ADC"

    return {
        "environment": env_val,
        "cuit": cuit_val,
        "punto_venta_default": pv_val,
        "dias_alerta_vencimiento": dias_alerta,
        "condicion_iva_emisor": cond_emisor,
        "condicion_iva_emisor_label": format_condicion_iva_emisor(cond_emisor),
        "nro_iibb": nro_iibb,
        "inicio_actividades": inicio_act,
        "cbu_fce_default": cbu_fce,
        "fce_sistema_circulacion": fce_sist,
    }


def save_arca_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Guarda y valida la configuración local de ARCA en data/certs/arca/arca_config.json.
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

    cond_raw = data.get("condicion_iva_emisor", current.get("condicion_iva_emisor"))
    cond_val = normalize_condicion_iva_emisor(cond_raw)

    nro_iibb_raw = data.get("nro_iibb", current.get("nro_iibb", cuit_val))
    nro_iibb_val = str(nro_iibb_raw if nro_iibb_raw is not None else cuit_val).strip()

    inicio_raw = data.get(
        "inicio_actividades", current.get("inicio_actividades", "01/01/2020")
    )
    inicio_val = str(inicio_raw or "01/01/2020").strip()

    cbu_raw = data.get("cbu_fce_default", current.get("cbu_fce_default", ""))
    cbu_val = _clean_cuit(cbu_raw) if cbu_raw else ""
    if cbu_val and len(cbu_val) != 22:
        raise ValueError("El CBU para FCE MiPyME debe tener exactamente 22 dígitos numéricos.")

    fce_sist_raw = data.get(
        "fce_sistema_circulacion", current.get("fce_sistema_circulacion", "ADC")
    )
    fce_sist_val = str(fce_sist_raw or "ADC").strip().upper()
    if fce_sist_val not in FCE_SISTEMAS_CIRCULACION:
        raise ValueError("El sistema de circulación FCE debe ser 'ADC' o 'SCA'.")

    new_config = {
        "environment": env_val,
        "cuit": cuit_val,
        "punto_venta_default": pv_val,
        "dias_alerta_vencimiento": dias_val,
        "condicion_iva_emisor": cond_val,
        "condicion_iva_emisor_label": format_condicion_iva_emisor(cond_val),
        "nro_iibb": nro_iibb_val,
        "inicio_actividades": inicio_val,
        "cbu_fce_default": cbu_val,
        "fce_sistema_circulacion": fce_sist_val,
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
    with _arca_lock("ta_cache_file"):
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
        raise ArcaServiceError(f"Entorno WSAA inválido: {environment}", status_http=400)

    cached = _load_cached_ta(env_clean, service)
    if cached:
        return cached

    with _arca_lock(f"ta_{env_clean}_{service}"):
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

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    wsaa_url, content=soap_envelope.encode("utf-8"), headers=headers
                )
        except httpx.HTTPError as exc:
            raise ArcaServiceError(
                f"Error de red al conectar con WSAA ({env_clean}): {exc}",
                status_http=502,
            ) from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise ArcaServiceError(
                f"Respuesta no-XML de WSAA ({env_clean}, HTTP {response.status_code}). "
                "El servidor de ARCA puede estar temporalmente fuera de servicio.",
                status_http=502,
            ) from exc

        fault_string = _find_text_local(root, "faultstring")
        if fault_string:
            fault_code = _find_text_local(root, "faultcode")
            raise ArcaServiceError(
                f"Error SOAP WSAA ({env_clean}): {fault_string}",
                code=fault_code,
                status_http=400,
            )

        if response.status_code >= 400:
            raise ArcaServiceError(
                f"WSAA devolvió HTTP {response.status_code} ({env_clean}).",
                status_http=502,
            )

        login_return = _find_text_local(root, "loginCmsReturn")
        if not login_return:
            raise ArcaServiceError(
                "Respuesta inválida de WSAA: no se encontró loginCmsReturn.",
                status_http=502,
            )

        try:
            ta_root = ET.fromstring(html.unescape(login_return))
        except ET.ParseError as exc:
            raise ArcaServiceError(
                "No se pudo interpretar el XML de loginCmsReturn devuelto por WSAA.",
                status_http=502,
            ) from exc

        token = _find_text_local(ta_root, "token")
        sign = _find_text_local(ta_root, "sign")
        exp_time = _find_text_local(ta_root, "expirationTime") or (
            datetime.now(timezone.utc) + timedelta(hours=12)
        ).isoformat()

        if not token or not sign:
            raise ArcaServiceError(
                "WSAA no devolvió Token o Sign válidos.",
                status_http=502,
            )

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
        raise ArcaServiceError(f"Entorno WSFEv1 inválido: {environment}", status_http=400)

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

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                WSFEV1_URLS[env_clean],
                content=soap_envelope.encode("utf-8"),
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise ArcaServiceError(
            f"Error de red al conectar con WSFEv1 ({action} en {env_clean}): {exc}",
            status_http=502,
        ) from exc

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise ArcaServiceError(
            f"Respuesta no-XML de WSFEv1 ({action}, HTTP {response.status_code}). "
            "El servicio de ARCA puede estar experimentando inconvenientes.",
            status_http=502,
        ) from exc

    fault_string = _find_text_local(root, "faultstring")
    if fault_string:
        fault_code = _find_text_local(root, "faultcode")
        raise ArcaServiceError(
            f"Error SOAP WSFEv1 ({action}): {fault_string}",
            code=fault_code,
            status_http=502 if response.status_code >= 500 else 400,
        )

    if response.status_code >= 400:
        raise ArcaServiceError(
            f"WSFEv1 ({action}) devolvió HTTP {response.status_code}.",
            status_http=502,
        )

    # Verificar bloque <Errors> de WSFEv1
    errors_msgs: list[str] = []
    first_code: str | None = None
    for elem in root.iter():
        if _strip_ns(elem.tag) == "Err":
            code = _find_text_local(elem, "Code") or ""
            msg = _find_text_local(elem, "Msg") or ""
            if code and first_code is None:
                first_code = code
            errors_msgs.append(f"[{code}] {msg}".strip())
    if errors_msgs:
        raise ArcaServiceError(
            f"Error WSFEv1 ({action}): {'; '.join(errors_msgs)}",
            code=first_code,
            status_http=400,
            observations=errors_msgs,
        )

    return root


def _parse_comprobante_asociado_str(
    raw_str: str | None,
    tipo_comprobante_actual: int,
    punto_venta_default: int,
) -> dict[str, Any] | None:
    """
    Intenta extraer (tipo, punto_venta, nro_comprobante) desde un string como
    '0001-00000015' o 'Factura A 0002-00000042'.
    """
    if not raw_str or not str(raw_str).strip():
        return None
    text = str(raw_str).strip()
    # Buscar patrón PV-NRO (ej. 0001-00000015 o 1-15)
    m = re.search(r"(\d{1,5})\s*[-/]\s*(\d{1,8})", text)
    if m:
        pv = int(m.group(1))
        nro = int(m.group(2))
    else:
        nums = re.findall(r"\d+", text)
        if not nums:
            return None
        if len(nums) >= 2:
            pv = int(nums[-2])
            nro = int(nums[-1])
        else:
            pv = int(punto_venta_default)
            nro = int(nums[0])

    # Inferir código de factura madre según la NC/ND actual
    cbte = int(tipo_comprobante_actual)
    if cbte in (2, 3):
        tipo_madre = 1
    elif cbte in (7, 8):
        tipo_madre = 6
    elif cbte in (12, 13):
        tipo_madre = 11
    elif cbte in (52, 53):
        tipo_madre = 51
    elif cbte in (202, 203):
        tipo_madre = 201
    elif cbte in (207, 208):
        tipo_madre = 206
    elif cbte in (212, 213):
        tipo_madre = 211
    else:
        tipo_madre = 1

    return {
        "tipo_comprobante": tipo_madre,
        "punto_venta": pv,
        "nro_comprobante": nro,
    }


class ArcaService:
    """
    Servicio de integración con ARCA/AFIP (WSAA y WSFEv1).
    Soporta todos los tipos de comprobantes electrónicos de mercado interno
    (Facturas A/B/C/M, Notas de Débito/Crédito, Recibos y FCE MiPyMEs),
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

    def fe_param_get_ptos_venta(self) -> list[dict[str, Any]]:
        """
        Consulta los Puntos de Venta habilitados para WSFEv1 en ARCA (FEParamGetPtosVenta).
        En modo mock retorna el punto de venta por defecto configurado.
        """
        cfg = get_arca_config()
        if self.use_mock or self.environment == "mock":
            return [
                {
                    "nro": int(cfg.get("punto_venta_default", 1)),
                    "emision_tipo": "RECE - MOCK",
                    "bloqueado": "N",
                    "fch_baja": None,
                }
            ]

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(cfg.get("cuit") or COMPANY_DATA.cuit)
        body_xml = (
            f'<FEParamGetPtosVenta xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            "</FEParamGetPtosVenta>"
        )
        root = _call_wsfev1_soap(self.environment, "FEParamGetPtosVenta", body_xml)
        ptos: list[dict[str, Any]] = []
        for elem in root.iter():
            if _strip_ns(elem.tag) == "PtoVenta":
                nro_str = _find_text_local(elem, "Nro")
                if nro_str and nro_str.isdigit():
                    ptos.append(
                        {
                            "nro": int(nro_str),
                            "emision_tipo": _find_text_local(elem, "EmisionTipo") or "",
                            "bloqueado": _find_text_local(elem, "Bloqueado") or "N",
                            "fch_baja": _find_text_local(elem, "FchBaja"),
                        }
                    )
        return ptos

    FEParamGetPtosVenta = fe_param_get_ptos_venta

    def fe_param_get_tipos_tributos(self) -> list[dict[str, Any]]:
        """
        Consulta los tipos de tributo vigentes en ARCA (FEParamGetTiposTributos).
        En modo mock (o si falla la consulta informativa) retorna el catálogo estándar.
        """
        if self.use_mock or self.environment == "mock":
            return list(TIPOS_TRIBUTO_CATALOGO)

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)
        body_xml = (
            f'<FEParamGetTiposTributos xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            "</FEParamGetTiposTributos>"
        )
        root = _call_wsfev1_soap(self.environment, "FEParamGetTiposTributos", body_xml)
        items: list[dict[str, Any]] = []
        for elem in root.iter():
            if _strip_ns(elem.tag) == "TributoTipo":
                id_str = _find_text_local(elem, "Id")
                desc = _find_text_local(elem, "Desc") or ""
                if id_str and id_str.isdigit():
                    items.append({"id": int(id_str), "descripcion": desc})
        return items or list(TIPOS_TRIBUTO_CATALOGO)

    FEParamGetTiposTributos = fe_param_get_tipos_tributos

    def fe_param_get_condicion_iva_receptor(self) -> list[dict[str, Any]]:
        """
        Consulta el catálogo de Condición frente al IVA del Receptor (FEParamGetCondicionIvaReceptor).
        """
        if self.use_mock or self.environment == "mock":
            return list(CONDICIONES_IVA_RECEPTOR_CATALOGO)

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)
        body_xml = (
            f'<FEParamGetCondicionIvaReceptor xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            "</FEParamGetCondicionIvaReceptor>"
        )
        root = _call_wsfev1_soap(self.environment, "FEParamGetCondicionIvaReceptor", body_xml)
        items: list[dict[str, Any]] = []
        for elem in root.iter():
            if _strip_ns(elem.tag) == "CondicionIvaReceptor":
                id_str = _find_text_local(elem, "Id")
                desc = _find_text_local(elem, "Desc") or ""
                cmp_clase = _find_text_local(elem, "Cmp_Clase") or ""
                if id_str and id_str.isdigit():
                    items.append(
                        {
                            "id": int(id_str),
                            "codigo": desc.upper(),
                            "descripcion": desc,
                            "clases_permitidas": [
                                c.strip() for c in cmp_clase.split("/") if c.strip()
                            ],
                        }
                    )
        return items or list(CONDICIONES_IVA_RECEPTOR_CATALOGO)

    FEParamGetCondicionIvaReceptor = fe_param_get_condicion_iva_receptor

    def fe_comp_consultar(
        self,
        punto_venta: int,
        tipo_comprobante: int,
        nro_comprobante: int,
    ) -> dict[str, Any] | None:
        """
        Consulta en ARCA un comprobante ya emitido (FECompConsultar) para conciliación.
        """
        if self.use_mock or self.environment == "mock":
            return None

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)
        body_xml = (
            f'<FECompConsultar xmlns="{FEV1_NS}">'
            "<Auth>"
            f"<Token>{html.escape(ta['token'])}</Token>"
            f"<Sign>{html.escape(ta['sign'])}</Sign>"
            f"<Cuit>{cuit_emisor}</Cuit>"
            "</Auth>"
            "<FeCompConsReq>"
            f"<CbteTipo>{int(tipo_comprobante)}</CbteTipo>"
            f"<CbteNro>{int(nro_comprobante)}</CbteNro>"
            f"<PtoVta>{int(punto_venta)}</PtoVta>"
            "</FeCompConsReq>"
            "</FECompConsultar>"
        )
        root = _call_wsfev1_soap(self.environment, "FECompConsultar", body_xml)
        cae = _find_text_local(root, "CodAutorizacion")
        if not cae:
            return None
        return {
            "punto_venta": int(punto_venta),
            "tipo_comprobante": int(tipo_comprobante),
            "nro_comprobante": int(nro_comprobante),
            "cae": cae,
            "vencimiento_cae": _find_text_local(root, "FchVto"),
            "fecha_emision": _find_text_local(root, "CbteFch"),
            "importe_total": float(_find_text_local(root, "ImpTotal") or 0.0),
            "resultado": _find_text_local(root, "Resultado"),
        }

    FECompConsultar = fe_comp_consultar

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
        SOAP FECAESolicitar de WSFEv1, cumpliendo con RG 5616/2024 y el orden
        estricto XSD del WSDL de ARCA.
        """
        cbte_tipo_int = int(tipo_comprobante)
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
                "tipo_comprobante": cbte_tipo_int,
                "cuit_cliente": cuit_cliente,
            }

        # Bloqueo explícito de Comprobantes de Exportación (Clase E) en entornos reales
        if cbte_tipo_int in CODIGOS_CLASE_E:
            raise ArcaServiceError(
                "Los comprobantes de exportación (Clase E) no están habilitados en WSFEv1.",
                code="CLASE_E_NO_SOPORTADA",
                status_http=400,
            )

        cfg = get_arca_config()
        cond_emisor = normalize_condicion_iva_emisor(cfg.get("condicion_iva_emisor"))
        if cond_emisor in ("MONOTRIBUTISTA", "EXENTO") and cbte_tipo_int not in CODIGOS_CLASE_C:
            raise ArcaServiceError(
                f"El emisor está configurado como {format_condicion_iva_emisor(cond_emisor)} "
                "y solo puede emitir comprobantes Clase C en ARCA.",
                status_http=400,
            )

        ta = self.obtener_ticket_acceso("wsfe")
        cuit_emisor = _clean_cuit(cfg.get("cuit") or COMPANY_DATA.cuit)

        concepto = int(kwargs.get("concepto_arca", 2) or 2)
        clean_doc = _clean_cuit(cuit_cliente)
        tipo_doc_str = str(kwargs.get("tipo_doc_receptor", "")).upper().strip()
        if clean_doc and len(clean_doc) == 11 and tipo_doc_str != "DNI":
            doc_tipo = 86 if tipo_doc_str == "CUIL" else 80
            doc_nro = int(clean_doc)
        elif clean_doc and len(clean_doc) >= 7 and clean_doc != "0" * len(clean_doc):
            doc_tipo = 96  # DNI
            doc_nro = int(clean_doc)
        else:
            doc_tipo = 99  # Consumidor Final
            doc_nro = 0

        condicion_iva_id = resolve_condicion_iva_receptor_id(
            kwargs.get("condicion_iva_receptor_id") or kwargs.get("condicion_iva_receptor"),
            tipo_comprobante=cbte_tipo_int,
            doc_tipo=doc_tipo,
        )

        imp_total = round(float(importe_total), 2)
        imp_no_gravado = round(float(kwargs.get("importe_no_gravado", 0.0) or 0.0), 2)
        imp_exento = round(float(kwargs.get("importe_exento", 0.0) or 0.0), 2)
        neto_0 = round(float(kwargs.get("neto_gravado_0", 0.0) or 0.0), 2)
        neto_21 = round(float(kwargs.get("neto_gravado_21", 0.0) or 0.0), 2)
        neto_105 = round(float(kwargs.get("neto_gravado_105", 0.0) or 0.0), 2)
        neto_27 = round(float(kwargs.get("neto_gravado_27", 0.0) or 0.0), 2)
        iva_21 = round(float(kwargs.get("iva_21", 0.0) or 0.0), 2)
        iva_105 = round(float(kwargs.get("iva_105", 0.0) or 0.0), 2)
        iva_27 = round(float(kwargs.get("iva_27", 0.0) or 0.0), 2)

        perc_iva = round(float(kwargs.get("percepcion_iva", 0.0) or 0.0), 2)
        perc_iibb = round(float(kwargs.get("percepcion_iibb", 0.0) or 0.0), 2)
        otros_imp = round(float(kwargs.get("otros_impuestos", 0.0) or 0.0), 2)
        imp_trib_explicit = kwargs.get("otros_tributos")
        if imp_trib_explicit is not None:
            imp_trib = round(float(imp_trib_explicit or 0.0), 2)
        else:
            imp_trib = round(perc_iva + perc_iibb + otros_imp, 2)

        if cbte_tipo_int in CODIGOS_CLASE_C:
            # Regla WSFEv1 para Comprobantes Clase C:
            # ImpOpEx = 0, ImpIVA = 0, sin bloque <Iva>, e ImpNeto = ImpTotal - ImpTotConc - ImpTrib
            imp_iva = 0.0
            imp_exento = 0.0
            imp_neto = round(max(0.0, imp_total - imp_no_gravado - imp_trib), 2)
            neto_0 = 0.0
            neto_21 = 0.0
            neto_105 = 0.0
            neto_27 = 0.0
            iva_21 = 0.0
            iva_105 = 0.0
            iva_27 = 0.0
        else:
            imp_neto = round(neto_0 + neto_21 + neto_105 + neto_27, 2)
            imp_iva = round(iva_21 + iva_105 + iva_27, 2)

            # Si no se pasó desglose explícito, inferir de importe_total
            if (imp_no_gravado + imp_exento + imp_neto + imp_iva + imp_trib) == 0.0 and imp_total > 0:
                imp_neto = round(imp_total / 1.21, 2)
                imp_iva = round(imp_total - imp_neto, 2)
                neto_21 = imp_neto
                iva_21 = imp_iva

            # Ajuste automático de $0.01 por redondeo en Factura B cuando ImpTotal difiere por 1 centavo
            suma_partes = round(imp_no_gravado + imp_exento + imp_neto + imp_iva + imp_trib, 2)
            diff_cent = round(imp_total - suma_partes, 2)
            if abs(diff_cent) == 0.01 and imp_iva > 0:
                if iva_21 > 0:
                    iva_21 = round(iva_21 + diff_cent, 2)
                elif iva_105 > 0:
                    iva_105 = round(iva_105 + diff_cent, 2)
                elif iva_27 > 0:
                    iva_27 = round(iva_27 + diff_cent, 2)
                imp_iva = round(iva_21 + iva_105 + iva_27, 2)

        cbte_fch = fecha_eff.strftime("%Y%m%d")
        f_desde = kwargs.get("fecha_servicio_desde") or fecha_eff
        f_hasta = kwargs.get("fecha_servicio_hasta") or fecha_eff
        f_vto = kwargs.get("fecha_vencimiento_pago") or fecha_eff

        serv_xml = ""
        if concepto in (2, 3):
            vto_tag = f"<FchVtoPago>{f_vto.strftime('%Y%m%d')}</FchVtoPago>"
            if cbte_tipo_int in CODIGOS_FCE_NOTA:
                vto_tag = ""
            serv_xml = (
                f"<FchServDesde>{f_desde.strftime('%Y%m%d')}</FchServDesde>"
                f"<FchServHasta>{f_hasta.strftime('%Y%m%d')}</FchServHasta>"
                f"{vto_tag}"
            )
        elif cbte_tipo_int in CODIGOS_FCE_FACTURA:
            serv_xml = f"<FchVtoPago>{f_vto.strftime('%Y%m%d')}</FchVtoPago>"

        # Bloque <CbtesAsoc> (Obligatorio para Notas de Crédito y Débito)
        cbtes_asoc_list = list(kwargs.get("comprobantes_asociados") or [])
        if not cbtes_asoc_list and kwargs.get("comprobante_asociado"):
            ca = kwargs["comprobante_asociado"]
            if isinstance(ca, dict):
                cbtes_asoc_list.append(ca)
        if not cbtes_asoc_list and kwargs.get("comprobante_asociado_str"):
            parsed_ca = _parse_comprobante_asociado_str(
                kwargs.get("comprobante_asociado_str"),
                cbte_tipo_int,
                int(punto_venta),
            )
            if parsed_ca:
                cbtes_asoc_list.append(parsed_ca)

        if cbte_tipo_int in CODIGOS_NOTA_CREDITO_DEBITO and not cbtes_asoc_list:
            raise ArcaServiceError(
                "Para emitir Notas de Crédito o Débito en ARCA es obligatorio informar el "
                "comprobante asociado (Tipo, Punto de Venta y Número).",
                status_http=400,
            )

        cbtes_asoc_xml = ""
        if cbtes_asoc_list:
            asoc_nodes: list[str] = []
            for item in cbtes_asoc_list:
                t_asoc = int(item.get("tipo_comprobante") or item.get("Tipo") or 1)
                pv_asoc = int(item.get("punto_venta") or item.get("PtoVta") or punto_venta)
                nro_asoc = int(item.get("nro_comprobante") or item.get("Nro") or 1)
                cuit_asoc = _clean_cuit(item.get("cuit") or item.get("Cuit") or cuit_emisor)
                fch_asoc_raw = item.get("fecha_emision") or item.get("CbteFch")
                fch_asoc_xml = ""
                if isinstance(fch_asoc_raw, date):
                    fch_asoc_xml = f"<CbteFch>{fch_asoc_raw.strftime('%Y%m%d')}</CbteFch>"
                elif isinstance(fch_asoc_raw, str) and fch_asoc_raw.strip():
                    clean_fch = fch_asoc_raw.strip().replace("-", "")
                    if len(clean_fch) == 8 and clean_fch.isdigit():
                        fch_asoc_xml = f"<CbteFch>{clean_fch}</CbteFch>"

                cuit_xml = f"<Cuit>{cuit_asoc}</Cuit>" if len(cuit_asoc) == 11 else ""
                asoc_nodes.append(
                    "<CbteAsoc>"
                    f"<Tipo>{t_asoc}</Tipo>"
                    f"<PtoVta>{pv_asoc}</PtoVta>"
                    f"<Nro>{nro_asoc}</Nro>"
                    f"{cuit_xml}"
                    f"{fch_asoc_xml}"
                    "</CbteAsoc>"
                )
            cbtes_asoc_xml = f"<CbtesAsoc>{''.join(asoc_nodes)}</CbtesAsoc>"

        # Bloque <Tributos> (Obligatorio cuando ImpTrib > 0)
        tributos_xml = ""
        if imp_trib > 0:
            tributos_list = list(kwargs.get("tributos") or [])
            if not tributos_list:
                base_ref = imp_neto if imp_neto > 0 else imp_total
                if perc_iva > 0:
                    alic_iva_p = round((perc_iva / base_ref) * 100, 2) if base_ref > 0 else 0.0
                    tributos_list.append(
                        {
                            "id": 1,
                            "desc": "Percepcion IVA",
                            "base_imp": base_ref,
                            "alic": alic_iva_p,
                            "importe": perc_iva,
                        }
                    )
                if perc_iibb > 0:
                    alic_iibb_p = round((perc_iibb / base_ref) * 100, 2) if base_ref > 0 else 0.0
                    tributos_list.append(
                        {
                            "id": 2,
                            "desc": "Percepcion IIBB",
                            "base_imp": base_ref,
                            "alic": alic_iibb_p,
                            "importe": perc_iibb,
                        }
                    )
                if otros_imp > 0:
                    tributo_otro_id = int(kwargs.get("tipo_tributo_otros_id") or 99)
                    alic_otro_p = round((otros_imp / base_ref) * 100, 2) if base_ref > 0 else 0.0
                    tributos_list.append(
                        {
                            "id": tributo_otro_id,
                            "desc": str(kwargs.get("desc_tributo_otros") or "Otros Tributos"),
                            "base_imp": base_ref,
                            "alic": alic_otro_p,
                            "importe": otros_imp,
                        }
                    )
                if not tributos_list:
                    tributos_list.append(
                        {
                            "id": 99,
                            "desc": "Otros Tributos",
                            "base_imp": base_ref,
                            "alic": 0.0,
                            "importe": imp_trib,
                        }
                    )

            trib_nodes: list[str] = []
            for t in tributos_list:
                t_id = int(t.get("id", 99))
                t_desc = html.escape(str(t.get("desc") or "Tributo"))
                t_base = round(float(t.get("base_imp", imp_neto) or 0.0), 2)
                t_alic = round(float(t.get("alic", 0.0) or 0.0), 2)
                t_imp = round(float(t.get("importe", 0.0) or 0.0), 2)
                if t_imp > 0:
                    trib_nodes.append(
                        "<Tributo>"
                        f"<Id>{t_id}</Id>"
                        f"<Desc>{t_desc}</Desc>"
                        f"<BaseImp>{t_base:.2f}</BaseImp>"
                        f"<Alic>{t_alic:.2f}</Alic>"
                        f"<Importe>{t_imp:.2f}</Importe>"
                        "</Tributo>"
                    )
            if trib_nodes:
                tributos_xml = f"<Tributos>{''.join(trib_nodes)}</Tributos>"

        # Bloque <Iva> (Solo comprobantes que discriminan / admiten AlicIva: A, B, M)
        iva_items_xml = ""
        if cbte_tipo_int not in CODIGOS_CLASE_C:
            alic_list: list[str] = []
            if neto_0 > 0:
                alic_list.append(
                    f"<AlicIva><Id>3</Id><BaseImp>{neto_0:.2f}</BaseImp><Importe>0.00</Importe></AlicIva>"
                )
            if neto_105 > 0 or iva_105 > 0:
                alic_list.append(
                    f"<AlicIva><Id>4</Id><BaseImp>{neto_105:.2f}</BaseImp><Importe>{iva_105:.2f}</Importe></AlicIva>"
                )
            if neto_21 > 0 or iva_21 > 0:
                alic_list.append(
                    f"<AlicIva><Id>5</Id><BaseImp>{neto_21:.2f}</BaseImp><Importe>{iva_21:.2f}</Importe></AlicIva>"
                )
            if neto_27 > 0 or iva_27 > 0:
                alic_list.append(
                    f"<AlicIva><Id>6</Id><BaseImp>{neto_27:.2f}</BaseImp><Importe>{iva_27:.2f}</Importe></AlicIva>"
                )
            if alic_list:
                iva_items_xml = f"<Iva>{''.join(alic_list)}</Iva>"

        # Bloque <Opcionales> (FCE MiPyME 201-213)
        opcionales_xml = ""
        opc_nodes: list[str] = []
        if cbte_tipo_int in CODIGOS_FCE_FACTURA:
            cbu_val = _clean_cuit(kwargs.get("cbu_emisor") or cfg.get("cbu_fce_default"))
            if len(cbu_val) != 22:
                raise ArcaServiceError(
                    "Para emitir Factura de Crédito Electrónica MiPyME (201/206/211) es obligatorio "
                    "informar un CBU de 22 dígitos.",
                    status_http=400,
                )
            sist_circ = str(
                kwargs.get("fce_sistema_circulacion")
                or cfg.get("fce_sistema_circulacion")
                or "ADC"
            ).strip().upper()
            if sist_circ not in FCE_SISTEMAS_CIRCULACION:
                sist_circ = "ADC"
            opc_nodes.append(f"<Opcional><Id>2101</Id><Valor>{cbu_val}</Valor></Opcional>")
            opc_nodes.append(f"<Opcional><Id>27</Id><Valor>{sist_circ}</Valor></Opcional>")
        elif cbte_tipo_int in CODIGOS_FCE_NOTA:
            es_anulacion_raw = kwargs.get("fce_anulacion", "N")
            if isinstance(es_anulacion_raw, bool):
                val_anul = "S" if es_anulacion_raw else "N"
            else:
                val_anul = "S" if str(es_anulacion_raw).strip().upper() in ("S", "SI", "TRUE", "1") else "N"
            opc_nodes.append(f"<Opcional><Id>22</Id><Valor>{val_anul}</Valor></Opcional>")

        for extra_opc in kwargs.get("opcionales") or []:
            opc_id = str(extra_opc.get("id") or "").strip()
            opc_val = str(extra_opc.get("valor") or "").strip()
            if opc_id and opc_val:
                opc_nodes.append(
                    f"<Opcional><Id>{html.escape(opc_id)}</Id><Valor>{html.escape(opc_val)}</Valor></Opcional>"
                )
        if opc_nodes:
            opcionales_xml = f"<Opcionales>{''.join(opc_nodes)}</Opcionales>"

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
            f"<CbteTipo>{cbte_tipo_int}</CbteTipo>"
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
            f"<CondicionIVAReceptorId>{condicion_iva_id}</CondicionIVAReceptorId>"
            f"{cbtes_asoc_xml}"
            f"{tributos_xml}"
            f"{iva_items_xml}"
            f"{opcionales_xml}"
            "</FECAEDetRequest>"
            "</FeDetReq>"
            "</FeCAEReq>"
            "</FECAESolicitar>"
        )

        root = _call_wsfev1_soap(self.environment, "FECAESolicitar", body_xml)
        resultado = _find_text_local(root, "Resultado")
        cae = _find_text_local(root, "CAE")
        cae_vto_str = _find_text_local(root, "CAEFchVto")

        obs_msgs: list[str] = []
        first_obs_code: str | None = None
        for elem in root.iter():
            if _strip_ns(elem.tag) == "Obs":
                code = _find_text_local(elem, "Code") or ""
                msg = _find_text_local(elem, "Msg") or ""
                if code and first_obs_code is None:
                    first_obs_code = code
                obs_msgs.append(f"[{code}] {msg}".strip())

        if resultado != "A" or not cae:
            detalle = "; ".join(obs_msgs) if obs_msgs else "Comprobante rechazado sin CAE."
            raise ArcaServiceError(
                f"ARCA rechazó el comprobante ({resultado}): {detalle}",
                code=first_obs_code,
                status_http=400,
                observations=obs_msgs,
            )

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
            "tipo_comprobante": cbte_tipo_int,
            "cuit_cliente": cuit_cliente,
            "condicion_iva_receptor_id": condicion_iva_id,
            "observaciones_arca": obs_msgs,
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
        En homologación o producción utiliza FECompUltimoAutorizado y FECAESolicitar
        bajo un lock inter-proceso por (cuit, punto_venta, tipo_comprobante).
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

        cuit_emisor = _clean_cuit(get_arca_config().get("cuit") or COMPANY_DATA.cuit)
        lock_key = f"emitir_{cuit_emisor}_{int(punto_venta)}_{int(tipo_comprobante)}"
        with _arca_lock(lock_key):
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
