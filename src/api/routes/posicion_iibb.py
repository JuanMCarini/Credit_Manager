from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, or_, and_
from typing import List, Optional
from datetime import date
from decimal import Decimal

from src.database import get_db
from src.database.models.finance.posicion_iibb import PosicionIibb, EstadoPosicionIibb
from src.database.models.finance.comprobantes import Comprobante, TipoComprobante
from src.database.models.creditos.facturacion import Factura
from src.database.models.finance.bancos import Movimiento, Concepto
from src.api.schemas.posicion_iibb import PosicionIibbCreate, PosicionIibbUpdate, PosicionIibbResponse

router = APIRouter(
    prefix="/api/finanzas/posicion-iibb",
    tags=["Finanzas - Posición IIBB"]
)

@router.get("", response_model=List[PosicionIibbResponse])
def get_posiciones(db: Session = Depends(get_db)):
    return db.query(PosicionIibb).order_by(PosicionIibb.anio.desc(), PosicionIibb.mes.desc()).all()

@router.get("/calcular")
def calcular_posicion(
    anio: int = Query(...),
    mes: int = Query(...),
    db: Session = Depends(get_db)
):
    # 1. Calcular Percepciones IIBB de Compras (de la tabla Comprobantes)
    comprobantes_result = db.query(
        func.sum(Comprobante.percepcion_iibb).label("percepcion_iibb")
    ).filter(
        extract('year', Comprobante.fecha_contable) == anio,
        extract('month', Comprobante.fecha_contable) == mes
    ).first()

    percepciones_compras = float(comprobantes_result.percepcion_iibb or 0)

    # 2. Calcular IIBB Ventas por Provincia (Cobranzas sobre interés + Facturas individuales de Finanzas, restando Notas de Crédito)
    from sqlalchemy.orm import joinedload
    from src.database.models.creditos.cobranzas import Cobranza
    from src.database.models.creditos.creditos import Credito, Cuota
    from src.database.models.creditos.clientes import Cliente, Provincia
    from src.database.models.creditos.facturacion import CODIGOS_NOTA_CREDITO
    from src.api.routes.facturacion import _extract_factura_breakdown

    facturas_mes = (
        db.query(Factura)
        .options(
            joinedload(Factura.cobranza)
            .joinedload(Cobranza.cuota)
            .joinedload(Cuota.credito)
            .joinedload(Credito.cliente)
            .joinedload(Cliente.provincia),
            joinedload(Factura.provincia),
        )
        .filter(
            extract('year', Factura.fecha_emision) == anio,
            extract('month', Factura.fecha_emision) == mes,
        )
        .all()
    )

    totales_por_prov: dict[tuple, float] = {}
    for fac in facturas_mes:
        bd = _extract_factura_breakdown(fac)
        signo = -1.0 if fac.tipo_comprobante in CODIGOS_NOTA_CREDITO else 1.0

        prov_obj = fac.provincia
        if (
            prov_obj is None
            and fac.cobranza
            and fac.cobranza.cuota
            and fac.cobranza.cuota.credito
            and fac.cobranza.cuota.credito.cliente
        ):
            prov_obj = fac.cobranza.cuota.credito.cliente.provincia

        prov_id = prov_obj.id if prov_obj else fac.provincia_id
        prov_nombre = prov_obj.nombre if prov_obj else "Sin Provincia"

        if fac.cobranza is not None:
            base_imponible = float(fac.cobranza.interes or 0.0)
        else:
            base_imponible = bd["neto_gravado_total"] + bd["importe_exento"]

        if base_imponible != 0:
            key = (prov_id, prov_nombre)
            totales_por_prov[key] = round(
                totales_por_prov.get(key, 0.0) + signo * base_imponible, 2
            )

    ventas_por_provincia = [
        {
            "provincia": prov_nombre,
            "provincia_id": prov_id,
            "neto": round(neto_val, 2),
        }
        for (prov_id, prov_nombre), neto_val in totales_por_prov.items()
        if neto_val != 0
    ]

    iibb_ventas = 0.0 # El frontend lo calculará con las alícuotas


    # 3. Retenciones Bancarias
    # Buscamos movimientos del mes donde el concepto contenga "iibb" o "sircreb"
    retenciones_result = db.query(
        func.sum(Movimiento.monto).label("retenciones")
    ).join(Concepto).filter(
        extract('year', Movimiento.fecha) == anio,
        extract('month', Movimiento.fecha) == mes,
        or_(
            Concepto.name.ilike('%sircreb%'), 
            and_(Concepto.name.ilike('%iibb%'), Concepto.name.ilike('%retencion%'))
        )
    ).first()

    retenciones_bancarias = abs(retenciones_result.retenciones) if retenciones_result and retenciones_result.retenciones else 0

    # 4. Pagos VEP de IIBB
    # Buscamos comprobantes tipo VEP asociados a conceptos de IIBB
    vep_comprobantes_result = db.query(
        func.sum(Comprobante.importe_total).label("total_vep")
    ).join(Concepto, Comprobante.concepto_id == Concepto.id).filter(
        extract('year', Comprobante.fecha_contable) == anio,
        extract('month', Comprobante.fecha_contable) == mes,
        Comprobante.tipo_comprobante == TipoComprobante.VEP,
        Concepto.name.ilike('%iibb%')
    ).first()

    # Y buscamos movimientos bancarios que correspondan a pagos de IIBB (VEP o Pago de Servicio)
    vep_movs_result = db.query(
        func.sum(Movimiento.monto).label("total_vep_mov")
    ).join(Concepto, Movimiento.concepto_id == Concepto.id).filter(
        extract('year', Movimiento.fecha) == anio,
        extract('month', Movimiento.fecha) == mes,
        or_(
            and_(Concepto.name.ilike('%vep%'), Concepto.name.ilike('%iibb%')),
            and_(Movimiento.descripcion.ilike('%pago%'), Concepto.name.ilike('%iibb%')),
            and_(Movimiento.descripcion.ilike('%vep%'), Concepto.name.ilike('%iibb%'))
        )
    ).first()

    total_veps_comp = float(vep_comprobantes_result.total_vep or 0)
    total_veps_mov = float(vep_movs_result.total_vep_mov or 0)
    
    pagos_vep = abs(total_veps_comp) + abs(total_veps_mov)

    # 5. Saldo Anterior a Favor
    if mes == 1:
        prev_mes = 12
        prev_anio = anio - 1
    else:
        prev_mes = mes - 1
        prev_anio = anio

    posicion_anterior = db.query(PosicionIibb).filter(
        PosicionIibb.anio == prev_anio,
        PosicionIibb.mes == prev_mes,
        PosicionIibb.estado == EstadoPosicionIibb.GUARDADO
    ).first()

    saldo_anterior = 0.0
    if posicion_anterior:
        saldo_anterior = float(posicion_anterior.saldo_a_pagar)

    return {
        "anio": anio,
        "mes": mes,
        "ventas_por_provincia": ventas_por_provincia,
        "iibb_ventas": iibb_ventas,
        "retenciones_bancarias": retenciones_bancarias,
        "percepciones_compras": percepciones_compras,
        "pagos_vep": pagos_vep,
        "saldo_anterior": saldo_anterior,
        "saldo_a_pagar": iibb_ventas - percepciones_compras - float(retenciones_bancarias) + saldo_anterior - pagos_vep
    }

@router.post("", response_model=PosicionIibbResponse)
def create_posicion(posicion: PosicionIibbCreate, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    db_pos = PosicionIibb(**posicion.model_dump())
    db.add(db_pos)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una posición guardada para este período.")
    db.refresh(db_pos)
    return db_pos

@router.put("/{posicion_id}", response_model=PosicionIibbResponse)
def update_posicion(posicion_id: int, posicion: PosicionIibbUpdate, db: Session = Depends(get_db)):
    db_pos = db.query(PosicionIibb).filter(PosicionIibb.id == posicion_id).first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Posición no encontrada")
    for key, value in posicion.model_dump(exclude_unset=True).items():
        setattr(db_pos, key, value)
    db.commit()
    db.refresh(db_pos)
    return db_pos

@router.delete("/{posicion_id}")
def delete_posicion(posicion_id: int, db: Session = Depends(get_db)):
    db_pos = db.query(PosicionIibb).filter(PosicionIibb.id == posicion_id).first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Posición no encontrada")
    db.delete(db_pos)
    db.commit()
    return {"message": "Posición eliminada correctamente"}
