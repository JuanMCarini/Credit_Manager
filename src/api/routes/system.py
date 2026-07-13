from fastapi import APIRouter, Depends, HTTPException
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
            else:
                all_cancelado = all(e == EstadoCredito.CANCELADO.value or e == "CANCELADO" for e in estados_str)
                if all_cancelado:
                    cli.estado = EstadoClienteEnum.INACTIVO
                else:
                    cli.estado = EstadoClienteEnum.ACTIVO

        db.commit()
        
        _LAST_SYNC_DATE = hoy
        _LAST_SYNC_STATE_HASH = current_state_hash
        
        return {"status": "success", "message": "Estados sincronizados correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company")
def get_company_info():
    from src.config import COMPANY_DATA
    return {
        "razon_social": COMPANY_DATA.razon_social,
        "cuit": COMPANY_DATA.cuit,
        "domicilio": COMPANY_DATA.domicilio,
        "email_contacto": COMPANY_DATA.email_contacto,
        "telefono": COMPANY_DATA.telefono
    }
