from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import date
import calendar
from typing import Dict, Any

from src.database import get_db
from src.database.models.creditos import Credito, Cuota
from src.database.models.cobranzas import Cobranza, TipoCobranzaEnum, Proceso, EstadoProcesoEnum
from src.database.models.socios import TasaYComision

router = APIRouter(
    prefix="/api/finanzas",
    tags=["Finanzas"]
)

def get_date_range(mes: str) -> tuple[date, date]:
    try:
        year_str, month_str = mes.split('-')
        year = int(year_str)
        month = int(month_str)
        
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de mes inválido. Use YYYY-MM")


@router.get("/comisiones/colocacion")
def calcular_colocacion(
    mes: str = Query(..., description="Mes en formato YYYY-MM"),
    db: Session = Depends(get_db)
):
    start_date, end_date = get_date_range(mes)
    
    # agrupacion_clave = (socio_id, plazo)
    socios_summary: Dict[tuple, Dict[str, Any]] = {}

    creditos = db.query(Credito).join(
        TasaYComision, Credito.comision_id == TasaYComision.id
    ).filter(
        Credito.fecha_emision >= start_date,
        Credito.fecha_emision <= end_date,
        Credito.comision_id.isnot(None)
    ).options(
        joinedload(Credito.comision).joinedload(TasaYComision.socio_originador),
        joinedload(Credito.comision).joinedload(TasaYComision.socio_intermediario)
    ).all()

    for credito in creditos:
        comision = credito.comision
        if not comision:
            continue
            
        plazo = credito.plazo
        
        # Originador
        if comision.socio_originador_id and comision.socio_originador:
            s_id = comision.socio_originador_id
            key = (s_id, plazo)
            if key not in socios_summary:
                socios_summary[key] = {
                    "socio_id": s_id,
                    "razon_social": comision.socio_originador.razon_social,
                    "plazo": plazo,
                    "total_capital": 0.0,
                    "total_colocacion_originador": 0.0,
                    "total_colocacion_intermediario": 0.0,
                    "total_comisiones": 0.0
                }
            
            monto_coloc = float(credito.capital) * float(comision.colocacion_originador)
            socios_summary[key]["total_capital"] += float(credito.capital)
            socios_summary[key]["total_colocacion_originador"] += monto_coloc
            socios_summary[key]["total_comisiones"] += monto_coloc
        
        # Intermediario
        if comision.socio_intermediario_id and comision.socio_intermediario:
            s_id = comision.socio_intermediario_id
            key = (s_id, plazo)
            if key not in socios_summary:
                socios_summary[key] = {
                    "socio_id": s_id,
                    "razon_social": comision.socio_intermediario.razon_social,
                    "plazo": plazo,
                    "total_capital": 0.0,
                    "total_colocacion_originador": 0.0,
                    "total_colocacion_intermediario": 0.0,
                    "total_comisiones": 0.0
                }
            
            monto_coloc = float(credito.capital) * float(comision.colocacion_intermediario)
            socios_summary[key]["total_capital"] += float(credito.capital)
            socios_summary[key]["total_colocacion_intermediario"] += monto_coloc
            socios_summary[key]["total_comisiones"] += monto_coloc

    resultado = [res for res in socios_summary.values() if res["total_comisiones"] > 0]
    resultado.sort(key=lambda x: (x["razon_social"], x["plazo"]))
    return resultado


@router.get("/comisiones/cobranza")
def calcular_cobranza(
    mes: str = Query(..., description="Mes en formato YYYY-MM"),
    db: Session = Depends(get_db)
):
    start_date, end_date = get_date_range(mes)

    # agrupacion_clave = (socio_id, fecha, proceso_id)
    socios_summary: Dict[tuple, Dict[str, Any]] = {}

    cobranzas = db.query(Cobranza).join(
        Cuota, Cobranza.cuota_id == Cuota.id
    ).join(
        Credito, Cuota.credito_id == Credito.id
    ).join(
        TasaYComision, Credito.comision_id == TasaYComision.id
    ).outerjoin(
        Proceso, Cobranza.proceso_id == Proceso.id
    ).filter(
        Cobranza.fecha >= start_date,
        Cobranza.fecha <= end_date,
        Cobranza.tipo_cobranza.notin_([
            TipoCobranzaEnum.BCA.value,
            TipoCobranzaEnum.CNC.value,
            TipoCobranzaEnum.AJUSTE.value
        ]),
        Credito.comision_id.isnot(None),
        or_(
            Cobranza.proceso_id.is_(None),
            Proceso.estado == EstadoProcesoEnum.COMPLETADO.value
        )
    ).options(
        joinedload(Cobranza.cuota).joinedload(Cuota.credito).joinedload(Credito.comision).joinedload(TasaYComision.socio_originador),
        joinedload(Cobranza.cuota).joinedload(Cuota.credito).joinedload(Credito.comision).joinedload(TasaYComision.socio_intermediario)
    ).all()

    for cobranza in cobranzas:
        if not cobranza.cuota or not cobranza.cuota.credito or not cobranza.cuota.credito.comision:
            continue
            
        comision = cobranza.cuota.credito.comision
        monto_cobrado = float(cobranza.capital) + float(cobranza.interes) + float(cobranza.iva)
        
        fecha_str = cobranza.fecha.isoformat() if cobranza.fecha else ""
        proceso_id = cobranza.proceso_id
        
        added_monto_keys = set()
        
        # Originador
        if comision.socio_originador_id and comision.socio_originador:
            s_id = comision.socio_originador_id
            key = (s_id, fecha_str, proceso_id)
            if key not in socios_summary:
                socios_summary[key] = {
                    "socio_id": s_id,
                    "razon_social": comision.socio_originador.razon_social,
                    "fecha": fecha_str,
                    "proceso_id": proceso_id,
                    "total_monto_cobrado": 0.0,
                    "total_cobranza_originador": 0.0,
                    "total_cobranza_intermediario": 0.0,
                    "total_comisiones": 0.0
                }
            
            monto_cob = monto_cobrado * float(comision.cobranza_originador)
            if key not in added_monto_keys:
                socios_summary[key]["total_monto_cobrado"] += monto_cobrado
                added_monto_keys.add(key)
            socios_summary[key]["total_cobranza_originador"] += monto_cob
            socios_summary[key]["total_comisiones"] += monto_cob
            
        # Intermediario
        if comision.socio_intermediario_id and comision.socio_intermediario:
            s_id = comision.socio_intermediario_id
            key = (s_id, fecha_str, proceso_id)
            if key not in socios_summary:
                socios_summary[key] = {
                    "socio_id": s_id,
                    "razon_social": comision.socio_intermediario.razon_social,
                    "fecha": fecha_str,
                    "proceso_id": proceso_id,
                    "total_monto_cobrado": 0.0,
                    "total_cobranza_originador": 0.0,
                    "total_cobranza_intermediario": 0.0,
                    "total_comisiones": 0.0
                }
                
            monto_cob = monto_cobrado * float(comision.cobranza_intermediario)
            if key not in added_monto_keys:
                socios_summary[key]["total_monto_cobrado"] += monto_cobrado
                added_monto_keys.add(key)
            socios_summary[key]["total_cobranza_intermediario"] += monto_cob
            socios_summary[key]["total_comisiones"] += monto_cob

    resultado = [res for res in socios_summary.values() if res["total_comisiones"] > 0]
    resultado.sort(key=lambda x: (x["razon_social"], x["fecha"]))
    return resultado
