import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date

from src.config import ROOT_DIR
from src.database import get_db
from src.database.models import Cuota, Credito, Cliente, EstadoCredito, EstadoClienteEnum, Cobranza
from src.database.models.auth import Usuario, TipoRolEnum
from src.api.dependencies.auth import get_current_user, admin_only

router = APIRouter(prefix="/api/v1/system", tags=["System"])

PUBLIC_ASSETS_DIR = (ROOT_DIR / "data" / "public").resolve()
UPLOADS_BASE_DIR = (ROOT_DIR / "data" / "uploads").resolve()
ALLOWED_UPLOAD_CATEGORIES = {"legajos", "contratos_carteras", "comprobantes", "cheques"}

_LAST_SYNC_DATE = None
_LAST_SYNC_STATE_HASH = None

@router.post("/sync-states", dependencies=[Depends(admin_only)])
@router.post("/actualizar_estados", dependencies=[Depends(admin_only)])
def sync_system_states(db: Session = Depends(get_db)):
    global _LAST_SYNC_DATE, _LAST_SYNC_STATE_HASH
    hoy = date.today()

    try:
        credito_stats = db.query(func.max(Credito.id), func.count(Credito.id)).first()
        cobranza_stats = db.query(func.max(Cobranza.id), func.count(Cobranza.id)).first()
        current_state_hash = f"cred:{credito_stats[0]}-{credito_stats[1]}_cob:{cobranza_stats[0]}-{cobranza_stats[1]}"
        
        if _LAST_SYNC_DATE == hoy and _LAST_SYNC_STATE_HASH == current_state_hash:
            return {"status": "success", "message": "Estados ya se encontraban sincronizados."}

        cuotas = db.query(Cuota).options(joinedload(Cuota.cobranzas), joinedload(Cuota.credito)).all()
        for c in cuotas:
            c.actualizar_estado(hoy)

        creditos = db.query(Credito).options(joinedload(Credito.cuotas)).all()
        for cred in creditos:
            if cred.fecha_emision == hoy:
                continue
            cred.actualizar_estado()
        
        clientes = db.query(Cliente).options(joinedload(Cliente.creditos)).all()
        for cli in clientes:
            creditos_cli = cli.creditos
            if not creditos_cli:
                cli.estado = EstadoClienteEnum.INACTIVO
                continue
            
            estados_str = []
            for cred in creditos_cli:
                e = cred.estado
                if isinstance(e, EstadoCredito):
                    estados_str.append(e.value)
                else:
                    estados_str.append(str(e))

            all_cancelado = all(e in [EstadoCredito.CANCELADO.value, "CANCELADO", EstadoCredito.RECHAZADO.value, "RECHAZADO"] for e in estados_str)
            if all_cancelado:
                cli.estado = EstadoClienteEnum.INACTIVO
            elif (
                EstadoCredito.JUDICIAL.value in estados_str
                or "JUDICIAL" in estados_str
                or EstadoCredito.INCOBRABLE.value in estados_str
                or "INCOBRABLE" in estados_str
            ):
                cli.estado = EstadoClienteEnum.INCOBRABLE
            elif EstadoCredito.MOROSO.value in estados_str or "MOROSO" in estados_str:
                cli.estado = EstadoClienteEnum.MOROSO
            else:
                cli.estado = EstadoClienteEnum.ACTIVO

        db.commit()
        
        _LAST_SYNC_DATE = hoy
        _LAST_SYNC_STATE_HASH = current_state_hash
        
        return {"status": "success", "message": "Estados sincronizados correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class CompanyUpdateSchema(BaseModel):
    razon_social: str
    cuit: str
    domicilio: str | None = None
    email_contacto: str | None = None
    telefono: str | None = None
    nro_cuenta_bancaria: str | None = None
    nombre_banco: str | None = None
    cbu: str | None = None
    dia_corte: int | None = None

@router.get("/company")
def get_company_info(db: Session = Depends(get_db)):
    from src.config import get_company_data
    company = get_company_data(db)
    return {
        "razon_social": company.razon_social,
        "cuit": company.cuit,
        "domicilio": company.domicilio,
        "email_contacto": company.email_contacto,
        "telefono": company.telefono,
        "nro_cuenta_bancaria": company.bank_account,
        "nombre_banco": company.bank_name,
        "cbu": company.cbu,
        "dia_corte": company.dia_corte
    }

@router.put("/company", dependencies=[Depends(admin_only)])
def update_company_info(data: CompanyUpdateSchema, db: Session = Depends(get_db)):
    from src.config import COMPANY_DATA, ENV_PATH, _sanitize_env_value, update_company_env
    from src.database.models.socios import SocioComercial
    
    # 1. Update DB record if exists (which also calls update_company_env)
    socio = db.query(SocioComercial).filter(SocioComercial.cuit == COMPANY_DATA.cuit).first()
    if socio:
        socio = SocioComercial.update_socio(
            socio_id=socio.id,
            db=db,
            razon_social=data.razon_social,
            cuit=data.cuit,
            domicilio_legal=data.domicilio,
            mail=data.email_contacto,
            telefono=data.telefono,
            nro_cuenta_bancaria=data.nro_cuenta_bancaria,
            nombre_banco=data.nombre_banco,
            cbu=data.cbu,
            dia_corte=data.dia_corte or 28
        )
        update_company_env(socio)
    else:
        # 2. Update .env file directly with sanitized values
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("COMPANY_RAZON_SOCIAL="):
                        f.write(f'COMPANY_RAZON_SOCIAL="{_sanitize_env_value(data.razon_social)}"\n')
                    elif line.startswith("COMPANY_CUIT="):
                        f.write(f'COMPANY_CUIT={_sanitize_env_value(data.cuit)}\n')
                    elif line.startswith("COMPANY_DOMICILIO="):
                        f.write(f'COMPANY_DOMICILIO="{_sanitize_env_value(data.domicilio)}"\n')
                    elif line.startswith("COMPANY_EMAIL_CONTACTO="):
                        f.write(f'COMPANY_EMAIL_CONTACTO="{_sanitize_env_value(data.email_contacto)}"\n')
                    elif line.startswith("COMPANY_TELEFONO="):
                        f.write(f'COMPANY_TELEFONO="{_sanitize_env_value(data.telefono)}"\n')
                    elif line.startswith("COMPANY_BANK_ACCOUNT="):
                        f.write(f'COMPANY_BANK_ACCOUNT="{_sanitize_env_value(data.nro_cuenta_bancaria)}"\n')
                    elif line.startswith("COMPANY_BANK_NAME="):
                        f.write(f'COMPANY_BANK_NAME="{_sanitize_env_value(data.nombre_banco)}"\n')
                    elif line.startswith("COMPANY_CBU="):
                        f.write(f'COMPANY_CBU="{_sanitize_env_value(data.cbu)}"\n')
                    elif line.startswith("COMPANY_DIA_CORTE="):
                        f.write(f'COMPANY_DIA_CORTE={int(data.dia_corte or 28)}\n')
                    else:
                        f.write(line)
                        
        # 3. Update runtime configuration
        COMPANY_DATA.razon_social = _sanitize_env_value(data.razon_social)
        COMPANY_DATA.cuit = _sanitize_env_value(data.cuit)
        COMPANY_DATA.domicilio = _sanitize_env_value(data.domicilio)
        COMPANY_DATA.email_contacto = _sanitize_env_value(data.email_contacto)
        COMPANY_DATA.telefono = _sanitize_env_value(data.telefono)
        COMPANY_DATA.bank_account = _sanitize_env_value(data.nro_cuenta_bancaria)
        COMPANY_DATA.bank_name = _sanitize_env_value(data.nombre_banco)
        COMPANY_DATA.cbu = _sanitize_env_value(data.cbu)
        COMPANY_DATA.dia_corte = int(data.dia_corte or 28)
    
    return {"status": "success", "message": "Datos de la empresa actualizados correctamente."}

@router.post("/repet/sync", dependencies=[Depends(admin_only)])
async def sync_repet(db: Session = Depends(get_db)):
    """
    Fuerza la sincronización manual de los listados del RePET.
    """
    from src.services.repet import sync_repet_data
    try:
        await sync_repet_data(db)
        return {"status": "success", "message": "Listados del RePET sincronizados correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logo")
def get_logo():
    """Sirve públicamente únicamente el logo institucional desde data/public (con fallback a data/uploads)."""
    for candidate in (PUBLIC_ASSETS_DIR / "logo.png", UPLOADS_BASE_DIR / "logo.png"):
        if candidate.is_file():
            return FileResponse(path=str(candidate), media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo no encontrado.")


@router.post("/logo", dependencies=[Depends(admin_only)])
async def upload_logo(file: UploadFile = File(...)):
    from src.utils.file_validation import stream_save_upload_file, validate_upload_file

    validate_upload_file(file, {".png", ".jpg", ".jpeg", ".webp"}, max_size_mb=10)
    
    PUBLIC_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    file_location = PUBLIC_ASSETS_DIR / "logo.png"
    
    try:
        stream_save_upload_file(file, file_location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {str(e)}")
        
    return {"status": "success", "message": "Logo actualizado correctamente. Recarga la página para ver los cambios."}


@router.get("/favicon")
def get_favicon_asset():
    """Sirve públicamente únicamente el favicon institucional desde data/public (con fallback a data/uploads)."""
    for candidate, media in (
        (PUBLIC_ASSETS_DIR / "favicon.png", "image/png"),
        (PUBLIC_ASSETS_DIR / "favicon.ico", "image/x-icon"),
        (UPLOADS_BASE_DIR / "favicon.png", "image/png"),
        (UPLOADS_BASE_DIR / "favicon.ico", "image/x-icon"),
    ):
        if candidate.is_file():
            return FileResponse(path=str(candidate), media_type=media)
    return Response(status_code=204)


@router.post("/favicon", dependencies=[Depends(admin_only)])
async def upload_favicon(file: UploadFile = File(...)):
    from src.utils.file_validation import validate_upload_file

    validate_upload_file(file, {".ico", ".png", ".jpg", ".jpeg", ".webp"}, max_size_mb=10)
    
    PUBLIC_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        content = await file.read()
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(content))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 1. Guardar PNG optimizado (192x192)
        png_img = img.copy()
        png_img.thumbnail((192, 192), Image.Resampling.LANCZOS)
        png_img.save(PUBLIC_ASSETS_DIR / "favicon.png", format="PNG", optimize=True)

        # 2. Guardar binario ICO genuino con múltiples resoluciones (16, 32, 48, 64)
        img.save(PUBLIC_ASSETS_DIR / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar y guardar el favicon: {str(e)}")
        
    return {"status": "success", "message": "Favicon actualizado y optimizado correctamente. Recarga la página para ver los cambios."}


@router.get("/uploads/{categoria}/{filename}")
def download_uploaded_file(
    categoria: str,
    filename: str,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Descarga segura y autenticada de documentos en data/uploads/{categoria}/{filename}.
    Valida estrictamente contra Path Traversal mediante Path.resolve().
    """
    if categoria not in ALLOWED_UPLOAD_CATEGORIES:
        raise HTTPException(status_code=400, detail="Categoría de documento inválida.")

    if not filename or Path(filename).name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")

    category_dir = (UPLOADS_BASE_DIR / categoria).resolve()
    target_path = (category_dir / filename).resolve()

    if not target_path.is_relative_to(UPLOADS_BASE_DIR) or not target_path.is_relative_to(category_dir):
        raise HTTPException(status_code=403, detail="Acceso denegado: ruta fuera del directorio permitido.")

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(path=str(target_path), filename=target_path.name)


from typing import Dict, List, Any
from src.database.models.system import ModuloSistema
from src.database.seed_modulos import seed_modulos

class ModuloUpdateSchema(BaseModel):
    creditos: bool | None = None
    cheques: bool | None = None
    inversores: bool | None = None
    finanzas: bool | None = None
    modulos: Dict[str, bool] | None = None

@router.get("/modules")
def get_system_modules(db: Session = Depends(get_db)):
    """
    Retorna el estado de activación de todas las secciones principales del sistema.
    """
    seed_modulos(db)
    mods = db.query(ModuloSistema).all()
    result = {m.codigo: m.activo for m in mods}
    items = [{"codigo": m.codigo, "nombre": m.nombre, "activo": m.activo} for m in mods]
    return {"modulos": result, "items": items}

@router.put("/modules", dependencies=[Depends(admin_only)])
def update_system_modules(
    payload: ModuloUpdateSchema,
    current_user: Usuario = Depends(admin_only),
    db: Session = Depends(get_db)
):
    """
    Actualiza el estado de las secciones del sistema.
    Exclusivo para usuarios con rol Administrador.
    """
    if current_user.rol.nombre != TipoRolEnum.ADMINISTRADOR:
        raise HTTPException(
            status_code=403,
            detail="Operación no permitida. Solo los administradores pueden modificar los módulos del sistema."
        )

    seed_modulos(db)
    updates = {}
    if payload.modulos:
        updates.update(payload.modulos)
    for k in ["creditos", "cheques", "inversores", "finanzas"]:
        val = getattr(payload, k, None)
        if val is not None:
            updates[k] = val

    for codigo, activo in updates.items():
        mod = db.query(ModuloSistema).filter(ModuloSistema.codigo == codigo).first()
        if mod:
            mod.activo = activo
    
    db.commit()

    mods = db.query(ModuloSistema).all()
    result = {m.codigo: m.activo for m in mods}
    items = [{"codigo": m.codigo, "nombre": m.nombre, "activo": m.activo} for m in mods]
    return {"status": "success", "message": "Módulos actualizados correctamente.", "modulos": result, "items": items}


# ==============================================================================
# ETAPA 3: Endpoints REST de Configuración y Estado ARCA (/api/v1/system/arca)
# ==============================================================================

import src.services.arca_service as arca_service


class ArcaConfigUpdateSchema(BaseModel):
    environment: str | None = None
    cuit: str | int | None = None
    punto_venta_default: int | None = None
    dias_alerta_vencimiento: int | None = None
    condicion_iva_emisor: str | None = None
    nro_iibb: str | None = None
    inicio_actividades: str | None = None
    cbu_fce_default: str | None = None
    fce_sistema_circulacion: str | None = None


class ArcaGenerarCsrSchema(BaseModel):
    cuit: str | int
    razon_social: str
    alias: str = "credit-manager-arca"


@router.get("/arca/status")
def get_arca_system_status(current_user: Usuario = Depends(get_current_user)):
    """
    Devuelve la configuración actual de ARCA (sin exponer rutas internas ni claves)
    junto con el estado de vigencia del certificado digital X.509.
    Accesible para cualquier usuario autenticado.
    """
    try:
        cfg = arca_service.get_arca_config()
        cert_info = arca_service.get_certificate_status()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    cuit_empresa = arca_service._clean_cuit(arca_service.COMPANY_DATA.cuit)
    cuit_coincide = not cuit_empresa or cuit_empresa == cfg["cuit"]

    return {
        "environment": cfg["environment"],
        "cuit": cfg["cuit"],
        "cuit_empresa": cuit_empresa,
        "cuit_coincide_empresa": cuit_coincide,
        "punto_venta_default": cfg["punto_venta_default"],
        "dias_alerta_vencimiento": cfg["dias_alerta_vencimiento"],
        "condicion_iva_emisor": cfg.get("condicion_iva_emisor", "RESPONSABLE_INSCRIPTO"),
        "condicion_iva_emisor_label": cfg.get(
            "condicion_iva_emisor_label", "IVA Responsable Inscripto"
        ),
        "nro_iibb": cfg.get("nro_iibb", cfg["cuit"]),
        "inicio_actividades": cfg.get("inicio_actividades", "01/01/2020"),
        "cbu_fce_default": cfg.get("cbu_fce_default", ""),
        "fce_sistema_circulacion": cfg.get("fce_sistema_circulacion", "ADC"),
        "config": cfg,
        "estado_vigencia": cert_info["estado"],
        "status": cert_info["status"],
        "estado": cert_info["estado"],
        "fecha_emision": cert_info["fecha_emision"],
        "fecha_vencimiento": cert_info["fecha_vencimiento"],
        "dias_restantes": cert_info["dias_restantes"],
        "alerta_vencimiento": bool(cert_info["alerta_vencimiento"]),
        "has_private_key": bool(cert_info["has_private_key"]),
        "has_csr": bool(cert_info["has_csr"]),
        "has_certificate": bool(cert_info["has_certificate"]),
        "subject": cert_info["subject"],
        "issuer": cert_info["issuer"],
        "serial_number": cert_info["serial_number"],
    }


@router.put("/arca/config", dependencies=[Depends(admin_only)])
def update_arca_system_config(
    payload: ArcaConfigUpdateSchema,
    current_user: Usuario = Depends(admin_only),
):
    """
    Actualiza los parámetros de configuración local de ARCA:
    environment, cuit, punto_venta_default y dias_alerta_vencimiento.
    """
    try:
        updated = arca_service.save_arca_config(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "message": "Configuración de ARCA actualizada correctamente.",
        "config": updated,
        **updated,
    }


@router.post("/arca/generar-csr", dependencies=[Depends(admin_only)])
def generate_arca_csr_endpoint(
    payload: ArcaGenerarCsrSchema,
    current_user: Usuario = Depends(admin_only),
):
    """
    Genera el par clave privada RSA 2048 (.key) + solicitud de certificado (.csr)
    a partir de cuit, razon_social y alias, y retorna el archivo .csr descargable.
    """
    try:
        res = arca_service.generar_key_y_csr(
            cuit=payload.cuit,
            razon_social=payload.razon_social,
            alias=payload.alias,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return Response(
        content=res["csr_pem"].encode("utf-8"),
        media_type="application/pkcs10",
        headers={"Content-Disposition": 'attachment; filename="arca.csr"'},
    )


@router.get("/arca/descargar-csr", dependencies=[Depends(admin_only)])
def download_arca_csr_endpoint(current_user: Usuario = Depends(admin_only)):
    """Descarga el archivo arca.csr generado en data/certs/arca/."""
    if not arca_service.ARCA_CSR_PATH.is_file():
        raise HTTPException(
            status_code=404,
            detail="No se encontró una solicitud de certificado generada (arca.csr).",
        )
    return Response(
        content=arca_service.ARCA_CSR_PATH.read_bytes(),
        media_type="application/pkcs10",
        headers={"Content-Disposition": 'attachment; filename="arca.csr"'},
    )


@router.get("/arca/descargar-key", dependencies=[Depends(admin_only)])
def download_arca_key_endpoint(current_user: Usuario = Depends(admin_only)):
    """Descarga el archivo arca.key generado en data/certs/arca/ para respaldo."""
    if not arca_service.ARCA_KEY_PATH.is_file():
        raise HTTPException(
            status_code=404,
            detail="No se encontró una clave privada generada (arca.key).",
        )
    return Response(
        content=arca_service.ARCA_KEY_PATH.read_bytes(),
        media_type="application/x-pem-file",
        headers={"Content-Disposition": 'attachment; filename="arca.key"'},
    )


@router.post("/arca/subir-certificado", dependencies=[Depends(admin_only)])
def upload_arca_certificate_endpoint(
    crt_file: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    certificado: UploadFile | None = File(default=None),
    cert: UploadFile | None = File(default=None),
    key_file: UploadFile | None = File(default=None),
    key: UploadFile | None = File(default=None),
    clave_privada: UploadFile | None = File(default=None),
    current_user: Usuario = Depends(admin_only),
):
    """
    Recibe vía UploadFile el archivo .crt (y opcionalmente .key), ejecuta la
    validación criptográfica y los almacena en data/certs/arca/.
    """
    target_crt = next(
        (f for f in (crt_file, file, certificado, cert) if hasattr(f, "file")),
        None,
    )
    if target_crt is None:
        raise HTTPException(
            status_code=400,
            detail="Debe adjuntar un archivo de certificado digital (.crt o .pem).",
        )

    crt_bytes = target_crt.file.read()
    target_key = next(
        (f for f in (key_file, key, clave_privada) if hasattr(f, "file")),
        None,
    )
    key_bytes = target_key.file.read() if target_key is not None else None

    try:
        meta = arca_service.guardar_y_validar_certificado(crt_bytes, key_bytes=key_bytes)
        cert_status = arca_service.get_certificate_status()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "message": "Certificado digital validado y almacenado correctamente.",
        "estado_vigencia": cert_status["estado"],
        "alerta_vencimiento": bool(cert_status["alerta_vencimiento"]),
        **meta,
    }


@router.post("/arca/probar-conexion", dependencies=[Depends(admin_only)])
def test_arca_connection_endpoint(current_user: Usuario = Depends(admin_only)):
    """
    Ejecuta FEDummy para verificar el estado de los servidores de ARCA y valida
    la obtención de Ticket de Acceso WSAA si existe un certificado cargado.
    """
    try:
        cfg = arca_service.get_arca_config()
        cert_status = arca_service.get_certificate_status()
        svc = arca_service.ArcaService()

        dummy_res = svc.fe_dummy()
        wsaa_ok = False
        wsaa_exp = None

        if cfg["environment"] == "mock":
            if cert_status["has_certificate"]:
                if cert_status["estado"] == "VENCIDO":
                    raise ValueError("El certificado digital cargado se encuentra vencido.")
                ta = svc.obtener_ticket_acceso("wsfe")
                wsaa_ok = bool(ta.get("token") and ta.get("sign"))
                wsaa_exp = ta.get("expiration_time")
        else:
            if not cert_status["has_certificate"]:
                raise ValueError(
                    "No existe un certificado digital (.crt) cargado para autenticar contra WSAA."
                )
            if cert_status["estado"] == "VENCIDO":
                raise ValueError("El certificado digital cargado se encuentra vencido.")
            ta = svc.obtener_ticket_acceso("wsfe")
            wsaa_ok = bool(ta.get("token") and ta.get("sign"))
            wsaa_exp = ta.get("expiration_time")

        puntos_venta_habilitados = []
        try:
            puntos_venta_habilitados = svc.fe_param_get_ptos_venta()
        except Exception:
            puntos_venta_habilitados = []

        return {
            "status": "success",
            "ok": bool(dummy_res.get("ok")),
            "environment": cfg["environment"],
            "dummy": dummy_res,
            "AppServer": dummy_res.get("AppServer"),
            "DbServer": dummy_res.get("DbServer"),
            "AuthServer": dummy_res.get("AuthServer"),
            "wsaa_autenticado": wsaa_ok,
            "wsaa_expiration": wsaa_exp,
            "puntos_venta_habilitados": puntos_venta_habilitados,
            "estado_vigencia": cert_status["estado"],
            "message": (
                "Conexión simulada exitosa en modo MOCK."
                if cfg["environment"] == "mock"
                else f"Conexión exitosa con ARCA ({cfg['environment']})."
            ),
        }
    except arca_service.ArcaServiceError as exc:
        raise HTTPException(status_code=exc.status_http or 400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Error al probar la conexión con ARCA: {str(exc)}",
        )



