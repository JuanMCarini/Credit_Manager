from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List, Optional
from datetime import date
from decimal import Decimal

from src.database import get_db
from src.database.models.finance.posicion_iva import PosicionIva
from src.database.models.finance.comprobantes import Comprobante
from src.database.models.creditos.facturacion import Factura
from src.database.models.finance.bancos import Movimiento, Concepto
from src.api.schemas.posicion_iva import PosicionIvaCreate, PosicionIvaUpdate, PosicionIvaResponse

router = APIRouter(
    prefix="/api/finanzas/posicion-iva",
    tags=["Finanzas - Posición IVA"]
)

@router.get("", response_model=List[PosicionIvaResponse])
def get_posiciones(db: Session = Depends(get_db)):
    return db.query(PosicionIva).order_by(PosicionIva.anio.desc(), PosicionIva.mes.desc()).all()

@router.get("/calcular")
def calcular_posicion(
    anio: int = Query(...),
    mes: int = Query(...),
    db: Session = Depends(get_db)
):
    # 1. Calcular IVA Compras y Percepciones (de la tabla Comprobantes)
    comprobantes_result = db.query(
        func.sum(Comprobante.iva_21).label("iva_21"),
        func.sum(Comprobante.iva_105).label("iva_105"),
        func.sum(Comprobante.iva_27).label("iva_27"),
        func.sum(Comprobante.percepcion_iva).label("percepcion_iva")
    ).filter(
        extract('year', Comprobante.fecha_contable) == anio,
        extract('month', Comprobante.fecha_contable) == mes
    ).first()

    iva_compras = sum([
        comprobantes_result.iva_21 or 0,
        comprobantes_result.iva_105 or 0,
        comprobantes_result.iva_27 or 0
    ])
    percepciones_compras = comprobantes_result.percepcion_iva or 0

    # 2. Calcular IVA Ventas (de Facturas emitidas)
    # Sumamos el campo 'iva' de la Cobranza asociada a las Facturas A (1) y B (6)
    from src.database.models.creditos.cobranzas import Cobranza
    facturas_result = db.query(
        func.sum(Cobranza.iva).label("total_iva")
    ).join(Factura, Factura.cobranza_id == Cobranza.id).filter(
        extract('year', Factura.fecha_emision) == anio,
        extract('month', Factura.fecha_emision) == mes,
        Factura.tipo_comprobante.in_([1, 6])
    ).first()

    iva_ventas = float(facturas_result.total_iva or 0)

    # 3. Retenciones Bancarias
    # Buscamos movimientos del mes donde el concepto contenga "IVA"
    retenciones_result = db.query(
        func.sum(Movimiento.monto).label("retenciones")
    ).join(Concepto).filter(
        extract('year', Movimiento.fecha) == anio,
        extract('month', Movimiento.fecha) == mes,
        Concepto.name.ilike('%iva%')
    ).first()

    retenciones_bancarias = abs(retenciones_result.retenciones) if retenciones_result and retenciones_result.retenciones else 0

    # 4. Pagos VEP de IVA
    # Buscamos comprobantes tipo VEP asociados a conceptos de IVA
    from src.database.models.finance.comprobantes import TipoComprobante
    vep_result = db.query(
        func.sum(Comprobante.importe_total).label("total_vep")
    ).join(Concepto, Comprobante.concepto_id == Concepto.id).filter(
        extract('year', Comprobante.fecha_contable) == anio,
        extract('month', Comprobante.fecha_contable) == mes,
        Comprobante.tipo_comprobante == TipoComprobante.VEP,
        Concepto.name.ilike('%iva%')
    ).first()

    total_veps = float(vep_result.total_vep or 0)
    pagos_vep = abs(total_veps)

    # 5. Saldo Anterior a Favor
    if mes == 1:
        prev_mes = 12
        prev_anio = anio - 1
    else:
        prev_mes = mes - 1
        prev_anio = anio

    from src.database.models.finance.posicion_iva import EstadoPosicionIva
    posicion_anterior = db.query(PosicionIva).filter(
        PosicionIva.anio == prev_anio,
        PosicionIva.mes == prev_mes,
        PosicionIva.estado == EstadoPosicionIva.GUARDADO
    ).first()

    saldo_anterior = 0.0
    if posicion_anterior:
        saldo_anterior = float(posicion_anterior.saldo_a_pagar)

    return {
        "anio": anio,
        "mes": mes,
        "iva_ventas": iva_ventas,
        "iva_compras": iva_compras,
        "retenciones_bancarias": retenciones_bancarias,
        "percepciones_compras": percepciones_compras,
        "pagos_vep": pagos_vep,
        "saldo_anterior": saldo_anterior,
        "saldo_a_pagar": float(iva_ventas) - float(iva_compras) - float(retenciones_bancarias) - float(percepciones_compras) + float(saldo_anterior)
    }

@router.post("", response_model=PosicionIvaResponse)
def create_posicion(posicion: PosicionIvaCreate, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    db_pos = PosicionIva(**posicion.model_dump())
    db.add(db_pos)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una posición guardada para este período.")
    db.refresh(db_pos)
    return db_pos

@router.put("/{posicion_id}", response_model=PosicionIvaResponse)
def update_posicion(posicion_id: int, posicion: PosicionIvaUpdate, db: Session = Depends(get_db)):
    db_pos = db.query(PosicionIva).filter(PosicionIva.id == posicion_id).first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Posición no encontrada")
    for key, value in posicion.model_dump(exclude_unset=True).items():
        setattr(db_pos, key, value)
    db.commit()
    db.refresh(db_pos)
    return db_pos

@router.delete("/{posicion_id}")
def delete_posicion(posicion_id: int, db: Session = Depends(get_db)):
    db_pos = db.query(PosicionIva).filter(PosicionIva.id == posicion_id).first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Posición no encontrada")
    db.delete(db_pos)
    db.commit()
    return {"message": "Posición eliminada correctamente"}
