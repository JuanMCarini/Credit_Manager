from fastapi import APIRouter, Depends, Query, HTTPException, Path, Body, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from datetime import date
import calendar
from typing import Dict, Any, List, Optional

from src.database import get_db
from src.database.models.creditos import Credito, Cuota
from src.database.models.cobranzas import Cobranza, TipoCobranzaEnum, Proceso, EstadoProcesoEnum
from src.database.models.socios import TasaYComision

# Nuevos imports para Bancos
from src.database.models.finance.bancos import Banco, Cuenta, Concepto, Clasificacion, Movimiento, CategoriaMovimiento
from src.api.schemas.bancos import (
    BancoCreate, BancoUpdate, BancoResponse,
    CuentaCreate, CuentaUpdate, CuentaResponse,
    ConceptoCreate, ConceptoUpdate, ConceptoResponse,
    MovimientoCreate, MovimientoUpdate, MovimientoResponse, MovimientoBulkConceptoUpdate,
    ClasificacionCreate, ClasificacionUpdate, ClasificacionResponse
)
from src.logic.import_data.bancos.bica import import_extract as bica_import
from src.logic.import_data.bancos.santander import import_extract as santander_import

PARSERS = {
    'bica': bica_import,
    'santander': santander_import
}

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

# -------------------------------------------------------------------
# Bancos
# -------------------------------------------------------------------
@router.get("/bancos", response_model=List[BancoResponse])
def get_bancos(db: Session = Depends(get_db)):
    return db.query(Banco).all()

@router.post("/bancos", response_model=BancoResponse)
def create_banco(banco: BancoCreate, db: Session = Depends(get_db)):
    db_banco = Banco(**banco.model_dump())
    db.add(db_banco)
    db.commit()
    db.refresh(db_banco)
    return db_banco

@router.put("/bancos/{banco_id}", response_model=BancoResponse)
def update_banco(banco_id: int, banco: BancoUpdate, db: Session = Depends(get_db)):
    db_banco = db.query(Banco).filter(Banco.id == banco_id).first()
    if not db_banco:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    for key, value in banco.model_dump(exclude_unset=True).items():
        setattr(db_banco, key, value)
    db.commit()
    db.refresh(db_banco)
    return db_banco

@router.delete("/bancos/{banco_id}")
def delete_banco(banco_id: int, db: Session = Depends(get_db)):
    db_banco = db.query(Banco).filter(Banco.id == banco_id).first()
    if not db_banco:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    db.delete(db_banco)
    db.commit()
    return {"message": "Banco eliminado correctamente"}

# -------------------------------------------------------------------
# Cuentas
# -------------------------------------------------------------------
@router.get("/cuentas", response_model=List[CuentaResponse])
def get_cuentas(db: Session = Depends(get_db)):
    cuentas = db.query(Cuenta).options(joinedload(Cuenta.banco)).all()
    # Pydantic will pull properties `saldo`, `saldo_fci`, `saldo_plazo_fijo` via from_attributes
    return cuentas

@router.get("/cuentas/{cuenta_id}/kpis")
def get_cuenta_kpis(
    cuenta_id: int, 
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db)
):
    cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    # Calcular según rango de fechas manualmente desde BD
    query = db.query(Movimiento).join(Concepto).filter(Movimiento.cuenta_id == cuenta_id)
    if fecha_desde:
        query = query.filter(Movimiento.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Movimiento.fecha <= fecha_hasta)
        
    movs = query.order_by(Movimiento.fecha, Movimiento.id).all()
    
    saldo = 0.0
    saldo_fci = 0.0
    saldo_pf = 0.0
    
    for m in movs:
        cat = m.concepto.tipo_movimiento
        
        # Saldo
        if cat in (CategoriaMovimiento.INGRESO, CategoriaMovimiento.RESCATE_FCI, CategoriaMovimiento.PLAZO_FIJO_EGRESOS):
            saldo += m.monto
        elif cat in (CategoriaMovimiento.EGRESO, CategoriaMovimiento.SUSCRIPCION_FCI, CategoriaMovimiento.PLAZO_FIJO_INGRESOS):
            saldo -= m.monto
            
        # FCI
        if cat == CategoriaMovimiento.SUSCRIPCION_FCI:
            saldo_fci += m.monto
        elif cat == CategoriaMovimiento.RESCATE_FCI:
            saldo_fci -= m.monto
        saldo_fci = max(0.0, saldo_fci)
            
        # PF
        if cat == CategoriaMovimiento.PLAZO_FIJO_INGRESOS:
            saldo_pf += m.monto
        elif cat == CategoriaMovimiento.PLAZO_FIJO_EGRESOS:
            saldo_pf -= m.monto
        saldo_pf = max(0.0, saldo_pf)

    return {
        "saldo": saldo,
        "saldo_fci": saldo_fci,
        "saldo_plazo_fijo": saldo_pf,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta
    }

@router.post("/cuentas", response_model=CuentaResponse)
def create_cuenta(cuenta: CuentaCreate, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    db_cuenta = Cuenta(**cuenta.model_dump())
    db.add(db_cuenta)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese nombre, CBU o Alias.")
    db.refresh(db_cuenta)
    return db_cuenta

@router.put("/cuentas/{cuenta_id}", response_model=CuentaResponse)
def update_cuenta(cuenta_id: int, cuenta: CuentaUpdate, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    db_cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not db_cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    for key, value in cuenta.model_dump(exclude_unset=True).items():
        setattr(db_cuenta, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese nombre, CBU o Alias.")
    db.refresh(db_cuenta)
    return db_cuenta

@router.delete("/cuentas/{cuenta_id}")
def delete_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    db_cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not db_cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    db.delete(db_cuenta)
    db.commit()
    return {"message": "Cuenta eliminada correctamente"}

@router.post("/cuentas/{cuenta_id}/importar-extracto")
def importar_extracto(
    cuenta_id: int, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verify account exists
    cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")

    if not cuenta.banco.parser_type or cuenta.banco.parser_type == 'none':
        raise HTTPException(status_code=400, detail="El banco de esta cuenta no soporta importación automática de extractos.")
        
    parser_func = PARSERS.get(cuenta.banco.parser_type.lower())
    if not parser_func:
        raise HTTPException(status_code=400, detail=f"Parser '{cuenta.banco.parser_type}' no está soportado.")

    try:
        # Pass the spooled temporary file directly to Pandas
        df = parser_func(file.file, cuenta_id)
        # Note: import_extract already commits new movimientos
        return {"message": "Extracto importado exitosamente", "filas_procesadas": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# Conceptos
# -------------------------------------------------------------------
@router.get("/conceptos", response_model=List[ConceptoResponse])
def get_conceptos(db: Session = Depends(get_db)):
    return db.query(Concepto).options(joinedload(Concepto.clasificacion)).all()

@router.post("/conceptos", response_model=ConceptoResponse)
def create_concepto(concepto: ConceptoCreate, db: Session = Depends(get_db)):
    db_concepto = Concepto(**concepto.model_dump())
    db.add(db_concepto)
    db.commit()
    db.refresh(db_concepto)
    return db_concepto

@router.put("/conceptos/{concepto_id}", response_model=ConceptoResponse)
def update_concepto(concepto_id: int, concepto: ConceptoUpdate, db: Session = Depends(get_db)):
    db_concepto = db.query(Concepto).filter(Concepto.id == concepto_id).first()
    if not db_concepto:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    for key, value in concepto.model_dump(exclude_unset=True).items():
        setattr(db_concepto, key, value)
    db.commit()
    db.refresh(db_concepto)
    return db_concepto

@router.delete("/conceptos/{concepto_id}")
def delete_concepto(concepto_id: int, db: Session = Depends(get_db)):
    db_concepto = db.query(Concepto).filter(Concepto.id == concepto_id).first()
    if not db_concepto:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    
    if getattr(db_concepto, 'is_system', False):
        raise HTTPException(status_code=400, detail="No se puede eliminar un concepto de sistema")
        
    db.delete(db_concepto)
    db.commit()
    return {"message": "Concepto eliminado correctamente"}

# -------------------------------------------------------------------
# Clasificaciones
# -------------------------------------------------------------------
@router.get("/clasificaciones", response_model=List[ClasificacionResponse])
def get_clasificaciones(db: Session = Depends(get_db)):
    return db.query(Clasificacion).all()

@router.post("/clasificaciones", response_model=ClasificacionResponse)
def create_clasificacion(clasificacion: ClasificacionCreate, db: Session = Depends(get_db)):
    db_clasificacion = Clasificacion(**clasificacion.model_dump())
    db.add(db_clasificacion)
    db.commit()
    db.refresh(db_clasificacion)
    return db_clasificacion

@router.put("/clasificaciones/{clasificacion_id}", response_model=ClasificacionResponse)
def update_clasificacion(clasificacion_id: int, clasificacion: ClasificacionUpdate, db: Session = Depends(get_db)):
    db_clasificacion = db.query(Clasificacion).filter(Clasificacion.id == clasificacion_id).first()
    if not db_clasificacion:
        raise HTTPException(status_code=404, detail="Clasificacion no encontrada")
    for key, value in clasificacion.model_dump(exclude_unset=True).items():
        setattr(db_clasificacion, key, value)
    db.commit()
    db.refresh(db_clasificacion)
    return db_clasificacion

@router.delete("/clasificaciones/{clasificacion_id}")
def delete_clasificacion(clasificacion_id: int, db: Session = Depends(get_db)):
    db_clasificacion = db.query(Clasificacion).filter(Clasificacion.id == clasificacion_id).first()
    if not db_clasificacion:
        raise HTTPException(status_code=404, detail="Clasificacion no encontrada")
    db.delete(db_clasificacion)
    db.commit()
    return {"message": "Clasificacion eliminada correctamente"}

# -------------------------------------------------------------------
# Movimientos
# -------------------------------------------------------------------
@router.get("/movimientos", response_model=List[MovimientoResponse])
def get_movimientos(
    cuenta_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    concepto_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Movimiento).options(
        joinedload(Movimiento.concepto).joinedload(Concepto.clasificacion),
        joinedload(Movimiento.cuenta)
    )
    if cuenta_id:
        query = query.filter(Movimiento.cuenta_id == cuenta_id)
    if fecha_desde:
        query = query.filter(Movimiento.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Movimiento.fecha <= fecha_hasta)
    if concepto_id:
        query = query.filter(Movimiento.concepto_id == concepto_id)
        
    return query.order_by(Movimiento.fecha.desc()).all()

@router.post("/movimientos", response_model=MovimientoResponse)
def create_movimiento(movimiento: MovimientoCreate, db: Session = Depends(get_db)):
    db_mov = Movimiento(**movimiento.model_dump())
    db.add(db_mov)
    db.commit()
    db.refresh(db_mov)
    return db_mov

@router.put("/movimientos/bulk-concepto")
def update_movimiento_bulk(data: MovimientoBulkConceptoUpdate, db: Session = Depends(get_db)):
    concepto = db.query(Concepto).filter(Concepto.id == data.concepto_id).first()
    if not concepto:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
        
    update_data = {"concepto_id": data.concepto_id}
        
    updated_count = db.query(Movimiento).filter(Movimiento.id.in_(data.movimiento_ids)).update(
        update_data, synchronize_session=False
    )
    db.commit()
    return {"message": f"Se actualizaron {updated_count} movimientos correctamente"}

@router.put("/movimientos/{movimiento_id}", response_model=MovimientoResponse)
def update_movimiento(movimiento_id: int, movimiento: MovimientoUpdate, db: Session = Depends(get_db)):
    db_mov = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not db_mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    for key, value in movimiento.model_dump(exclude_unset=True).items():
        setattr(db_mov, key, value)
    db.commit()
    db.refresh(db_mov)
    return db_mov

@router.delete("/movimientos/{movimiento_id}")
def delete_movimiento(movimiento_id: int, db: Session = Depends(get_db)):
    db_mov = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not db_mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    db.delete(db_mov)
    db.commit()
    return {"message": "Movimiento eliminado correctamente"}

