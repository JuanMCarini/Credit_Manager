import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date

from src.database import get_db
from src.database.models import Cuota, Credito, Cliente, EstadoCredito, EstadoClienteEnum, Cobranza

router = APIRouter(prefix="/api/v1/system", tags=["System"])

_LAST_SYNC_DATE = None
_LAST_SYNC_STATE_HASH = None

@router.post("/sync-states")
@router.post("/actualizar_estados")
def sync_system_states(db: Session = Depends(get_db)):
    global _LAST_SYNC_DATE, _LAST_SYNC_STATE_HASH
    hoy = date.today()

    try:
        credito_stats = db.query(func.max(Credito.id), func.count(Credito.id)).first()
        cobranza_stats = db.query(func.max(Cobranza.id), func.count(Cobranza.id)).first()
        current_state_hash = f"cred:{credito_stats[0]}-{credito_stats[1]}_cob:{cobranza_stats[0]}-{cobranza_stats[1]}"
        
        if _LAST_SYNC_DATE == hoy and _LAST_SYNC_STATE_HASH == current_state_hash:
            return {"status": "success", "message": "Estados ya se encontraban sincronizados."}

        cuotas = db.query(Cuota).options(joinedload(Cuota.cobranzas)).all()
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

            if EstadoCredito.JUDICIAL.value in estados_str or "JUDICIAL" in estados_str:
                cli.estado = EstadoClienteEnum.INCOBRABLE
            elif EstadoCredito.MOROSO.value in estados_str or "MOROSO" in estados_str:
                cli.estado = EstadoClienteEnum.MOROSO
            elif EstadoCredito.CANCELADO.value in estados_str or "CANCELADO" in estados_str:
                all_cancelado = all(e == EstadoCredito.CANCELADO.value or e == "CANCELADO" for e in estados_str)
                if all_cancelado:
                    cli.estado = EstadoClienteEnum.INACTIVO
                else:
                    cli.estado = EstadoClienteEnum.ACTIVO
            elif EstadoCredito.FIRMADO.value in estados_str or "FIRMADO" in estados_str:
                cli.estado = EstadoClienteEnum.ACTIVO
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

@router.put("/company")
def update_company_info(data: CompanyUpdateSchema, db: Session = Depends(get_db)):
    from src.config import COMPANY_DATA
    from src.database.models.socios import SocioComercial
    
    # 1. Update DB record if exists
    socio = db.query(SocioComercial).filter(SocioComercial.cuit == COMPANY_DATA.cuit).first()
    if socio:
        SocioComercial.update_socio(
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
        
    # 2. Update .env file
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        with open(env_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("COMPANY_RAZON_SOCIAL="):
                    f.write(f'COMPANY_RAZON_SOCIAL="{data.razon_social}"\n')
                elif line.startswith("COMPANY_CUIT="):
                    f.write(f'COMPANY_CUIT={data.cuit}\n')
                elif line.startswith("COMPANY_DOMICILIO="):
                    f.write(f'COMPANY_DOMICILIO="{data.domicilio or ""}"\n')
                elif line.startswith("COMPANY_EMAIL_CONTACTO="):
                    f.write(f'COMPANY_EMAIL_CONTACTO="{data.email_contacto or ""}"\n')
                elif line.startswith("COMPANY_TELEFONO="):
                    f.write(f'COMPANY_TELEFONO="{data.telefono or ""}"\n')
                elif line.startswith("COMPANY_BANK_ACCOUNT="):
                    f.write(f'COMPANY_BANK_ACCOUNT="{data.nro_cuenta_bancaria or ""}"\n')
                elif line.startswith("COMPANY_BANK_NAME="):
                    f.write(f'COMPANY_BANK_NAME="{data.nombre_banco or ""}"\n')
                elif line.startswith("COMPANY_CBU="):
                    f.write(f'COMPANY_CBU="{data.cbu or ""}"\n')
                elif line.startswith("COMPANY_DIA_CORTE="):
                    f.write(f'COMPANY_DIA_CORTE={data.dia_corte or 28}\n')
                else:
                    f.write(line)
                    
    # 3. Update runtime configuration
    COMPANY_DATA.razon_social = data.razon_social
    COMPANY_DATA.cuit = data.cuit
    COMPANY_DATA.domicilio = data.domicilio or ""
    COMPANY_DATA.email_contacto = data.email_contacto or ""
    COMPANY_DATA.telefono = data.telefono or ""
    COMPANY_DATA.bank_account = data.nro_cuenta_bancaria or ""
    COMPANY_DATA.bank_name = data.nombre_banco or ""
    COMPANY_DATA.cbu = data.cbu or ""
    COMPANY_DATA.dia_corte = data.dia_corte or 28
    
    return {"status": "success", "message": "Datos de la empresa actualizados correctamente."}

@router.post("/repet/sync")
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

@router.post("/logo")
async def upload_logo(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    
    os.makedirs("data/uploads", exist_ok=True)
    file_location = "data/uploads/logo.png"
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {str(e)}")
        
    return {"status": "success", "message": "Logo actualizado correctamente. Recarga la página para ver los cambios."}

from typing import Dict, List, Any
from src.database.models.system import ModuloSistema
from src.database.models.auth import Usuario, TipoRolEnum
from src.api.dependencies.auth import get_current_user
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

@router.put("/modules")
def update_system_modules(
    payload: ModuloUpdateSchema,
    current_user: Usuario = Depends(get_current_user),
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


