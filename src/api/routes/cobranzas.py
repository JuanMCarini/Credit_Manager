from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from src.database import get_db
from src.logic.collections import CollectionManager
from src.api.schemas.cobranzas import CobranzaIndividual, CobranzaMasiva, CobranzaRecurso, ProcesoUpdate
from src.api.dependencies.auth import get_current_user
from src.database.models.auth import Usuario, RegistroAuditoria

router = APIRouter(prefix="/api/v1", tags=["Cobranzas"])

@router.post("/cobranzas/individual")
def procesar_cobranza_individual(
    request: Request,
    datos: CobranzaIndividual,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(datos.fecha_pago, datetime.min.time()) if datos.fecha_pago else datetime.today()
        fecha_corte_dt = datetime.combine(datos.fecha_corte, datetime.min.time()) if datos.fecha_corte else None
        if datos.anticipada:
            df = manager.process_early_cancellation(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt,
                vto_date=fecha_corte_dt
            )
        else:
            df = manager.process_standard_payment(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt,
                vto_date=fecha_corte_dt
            )
        
        if df.empty:
            raise ValueError("No se encontraron cuotas pendientes para el identificador proporcionado o la cobranza resultó vacía.")
            
        proceso_id = df.attrs.get("proceso_id") if hasattr(df, "attrs") else None
        
        tipo_cob_solicitado = datos.tipo_cobranza or "COMUN"
        
        if not datos.anticipada and proceso_id and tipo_cob_solicitado in ["COMUN", "AJUSTE"]:
            from src.database.models.cobranzas import Cobranza, TipoCobranzaEnum
            from src.database.models.creditos import Credito, Cuota
            
            cobranzas = db.query(Cobranza).filter(Cobranza.proceso_id == proceso_id).all()
            for cob in cobranzas:
                tipo_actual = cob.tipo_cobranza.value if hasattr(cob.tipo_cobranza, 'value') else cob.tipo_cobranza
                if tipo_actual not in (TipoCobranzaEnum.COMUN.value, TipoCobranzaEnum.ANTICIPO.value):
                    continue
                
                if tipo_cob_solicitado == "AJUSTE":
                    cob.tipo_cobranza = TipoCobranzaEnum.AJUSTE.value
                elif tipo_cob_solicitado == "COMUN":
                    credito = cob.cuota.credito if cob.cuota else None
                    if credito and credito.cartera and credito.cartera.recurso:
                        cob.tipo_cobranza = TipoCobranzaEnum.RECURSO.value
                    else:
                        if cob.cuota and cob.cuota.fecha_vencimiento and cob.cuota.fecha_vencimiento > fecha_pago_dt.date():
                            cob.tipo_cobranza = TipoCobranzaEnum.ANTICIPO.value
                        else:
                            cob.tipo_cobranza = TipoCobranzaEnum.COMUN.value
            db.commit()

        accion_text = f"Crear Proceso Individual (ID: {proceso_id}) - {datos.identificador}: {datos.id_val}" if proceso_id else f"Crear Cobranza Individual - {datos.identificador}: {datos.id_val}"

        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion_text,
            endpoint=request.url.path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito"
        )
        db.add(log)
        db.commit()

        return {"status": "success", "message": "Cobranza individual procesada exitosamente.", "proceso_id": proceso_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cobranzas/masiva")
def procesar_cobranza_masiva(
    request: Request,
    identificador: str = Form(...),
    id_column: str = Form("A"),
    amount_column: str = Form("B"),
    fecha_pago: Optional[date] = Form(None),
    fecha_corte: Optional[date] = Form(None),
    anticipada: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(fecha_pago, datetime.min.time()) if fecha_pago else datetime.today()
        fecha_corte_dt = datetime.combine(fecha_corte, datetime.min.time()) if fecha_corte else None
        file_bytes = file.file.read()
        
        df = manager.process_massive_collection(
            identificador=identificador,
            id_column=id_column,
            amount_column=amount_column,
            payment_date=fecha_pago_dt,
            vto_date=fecha_corte_dt,
            early=anticipada,
            file_bytes=file_bytes,
            filename=file.filename
        )
        
        proceso_id = df.attrs.get("proceso_id") if hasattr(df, "attrs") else None

        accion_text = f"Crear Proceso Masivo (ID: {proceso_id}) - {identificador}" if proceso_id else f"Crear Cobranza Masiva - {identificador}"

        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion_text,
            endpoint=request.url.path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito"
        )
        db.add(log)
        db.commit()

        return {"status": "success", "message": "Cobranza masiva procesada exitosamente.", "proceso_id": proceso_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cobranzas/recurso")
def procesar_cobranza_recurso(
    request: Request,
    datos: CobranzaRecurso,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(datos.fecha_pago, datetime.min.time()) if datos.fecha_pago else datetime.today()
        
        df = manager.process_resource(
            identificador=datos.identificador,
            id_val=datos.id_val,
            amount=datos.monto,
            payment_date=fecha_pago_dt
        )
        
        proceso_id = df.attrs.get("proceso_id") if hasattr(df, "attrs") else None
        anticipos_previos = df.attrs.get("anticipos_previos", 0.0) if hasattr(df, "attrs") else 0.0
        sobrante = df.attrs.get("sobrante", 0.0) if hasattr(df, "attrs") else 0.0
        anticipos_actualizado = df.attrs.get("anticipos_actualizado", 0.0) if hasattr(df, "attrs") else 0.0
        
        # Build dynamic message
        if not proceso_id:
            message = f"No se cobraron cuotas. Se agregaron ${sobrante:,.2f} a anticipos. Anticipo acumulado total: ${anticipos_actualizado:,.2f}."
        else:
            if sobrante > 0:
                message = f"Cobranza procesada. ID: {proceso_id}. Sobró dinero y se mandaron ${sobrante:,.2f} a anticipos. Anticipo acumulado: ${anticipos_actualizado:,.2f}."
            elif sobrante < 0:
                message = f"Cobranza procesada. ID: {proceso_id}. Se usaron ${abs(sobrante):,.2f} de anticipos previos. Anticipo remanente: ${anticipos_actualizado:,.2f}."
            else:
                message = f"Cobranza procesada. ID: {proceso_id}."
        
        accion_text = f"Crear Proceso Recurso (ID: {proceso_id}) - {datos.identificador}: {datos.id_val}" if proceso_id else f"Crear Cobranza Recurso (Sin Proceso) - {datos.identificador}: {datos.id_val}"

        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion_text,
            endpoint=request.url.path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito"
        )
        db.add(log)
        db.commit()

        return {"status": "success", "message": message, "proceso_id": proceso_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/procesos")
def get_procesos(db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso, Cobranza
    from sqlalchemy import func
    
    procesos = db.query(Proceso).order_by(desc(Proceso.fecha_ejecucion)).all()
    
    totals_query = db.query(
        Cobranza.proceso_id,
        func.sum(Cobranza.capital).label("capital"),
        func.sum(Cobranza.interes).label("interes"),
        func.sum(Cobranza.iva).label("iva"),
        func.sum(Cobranza.capital + Cobranza.interes + Cobranza.iva).label("total")
    ).group_by(Cobranza.proceso_id).all()
    
    totals_map = {
        t.proceso_id: {
            "capital": float(t.capital or 0),
            "interes": float(t.interes or 0),
            "iva": float(t.iva or 0),
            "total": float(t.total or 0)
        } for t in totals_query if t.proceso_id is not None
    }
    
    result = []
    for p in procesos:
        p_totals = totals_map.get(p.id, {"capital": 0.0, "interes": 0.0, "iva": 0.0, "total": 0.0})
        result.append({
            "ID": p.id,
            "Tipo": p.tipo.value if hasattr(p.tipo, 'value') else str(p.tipo),
            "Estado": p.estado.value if hasattr(p.estado, 'value') else str(p.estado),
            "Descripción": p.descripcion or "-",
            "Fecha Ejecución": p.fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_ejecucion else "-",
            "Capital": p_totals["capital"],
            "Interes": p_totals["interes"],
            "IVA": p_totals["iva"],
            "Total": p_totals["total"]
        })
    return result

@router.put("/procesos/{proceso_id}")
def update_proceso(proceso_id: int, data: ProcesoUpdate, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso, EstadoProcesoEnum
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    
    try:
        nuevo_estado = EstadoProcesoEnum(data.estado.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido.")
        
    proceso.estado = nuevo_estado
    if data.descripcion is not None:
        proceso.descripcion = data.descripcion
        
    db.commit()
    return {"status": "success", "message": "Proceso actualizado"}

from pydantic import BaseModel

class PagoProcesoRequest(BaseModel):
    monto: float
    fecha_pago: date

@router.post("/procesos/{proceso_id}/liquidaciones/pagar")
def pagar_proceso_liquidaciones(
    proceso_id: int, 
    data: PagoProcesoRequest, 
    db: Session = Depends(get_db)
):
    from src.database.models.cobranzas import Proceso, EstadoProcesoEnum, TipoProcesoEnum, LiquidacionCuotaCedida, TipoLiquidacionEnum
    from src.database.models.socios import AnticiposSinAplicar
    from src.logic.settlements import SettlementManager
    from sqlalchemy import func
    
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
        
    if proceso.tipo not in [TipoProcesoEnum.LIQUIDACIONES_MASIVAS, TipoProcesoEnum.LIQUIDACIONES_INDIVIDUALES]:
        raise HTTPException(status_code=400, detail="El proceso no es de liquidaciones.")
        
    if proceso.estado == EstadoProcesoEnum.COMPLETADO:
        raise HTTPException(status_code=400, detail="El proceso ya está COMPLETADO.")
        
    liq = db.query(LiquidacionCuotaCedida).filter(LiquidacionCuotaCedida.proceso_id == proceso_id).first()
    socio_id = liq.cartera.socio_id if liq and liq.cartera else None
    
    if not socio_id:
        raise HTTPException(status_code=400, detail="No se pudo determinar el Socio Comercial para este proceso.")
    
    try:
        if data.monto > 0:
            db.add(AnticiposSinAplicar(fecha=data.fecha_pago, socio_id=socio_id, monto=data.monto))
            db.flush()
            
        saldo_anticipos = db.query(func.sum(AnticiposSinAplicar.monto)).filter(AnticiposSinAplicar.socio_id == socio_id).scalar() or 0.0
        saldo_anticipos = float(saldo_anticipos)
        
        deuda_proceso_recurso = db.query(
            func.sum(LiquidacionCuotaCedida.capital + LiquidacionCuotaCedida.interes + LiquidacionCuotaCedida.iva)
        ).filter(
            LiquidacionCuotaCedida.proceso_id == proceso_id,
            LiquidacionCuotaCedida.cancelada == False,
            LiquidacionCuotaCedida.tipo_liquidacion == TipoLiquidacionEnum.RECURSO.value
        ).scalar() or 0.0
        deuda_proceso_recurso = float(deuda_proceso_recurso)
        
        deuda_proceso_sin_recurso = db.query(
            func.sum(LiquidacionCuotaCedida.capital + LiquidacionCuotaCedida.interes + LiquidacionCuotaCedida.iva)
        ).filter(
            LiquidacionCuotaCedida.proceso_id == proceso_id,
            LiquidacionCuotaCedida.cancelada == False,
            LiquidacionCuotaCedida.tipo_liquidacion != TipoLiquidacionEnum.RECURSO.value
        ).scalar() or 0.0
        deuda_proceso_sin_recurso = float(deuda_proceso_sin_recurso)
        
        mensaje = ""
        if data.monto > 0:
            mensaje += f"Se ingresó el pago de ${data.monto:.2f} a los anticipos. "
            
        if deuda_proceso_recurso == 0 and deuda_proceso_sin_recurso == 0:
            proceso.estado = EstadoProcesoEnum.COMPLETADO
            db.commit()
            return {"status": "success", "message": mensaje + "El proceso no tiene deuda pendiente."}

        sm = SettlementManager(db)

        if deuda_proceso_recurso > 0:
            if saldo_anticipos >= deuda_proceso_recurso:
                db.add(AnticiposSinAplicar(fecha=data.fecha_pago, socio_id=socio_id, monto=-deuda_proceso_recurso))
                
                df, _, cant_recurso = sm.canceled_settlements(
                    fecha_pago=data.fecha_pago,
                    amount=0,
                    proceso_id=proceso_id,
                    tipos_liquidacion=[TipoLiquidacionEnum.RECURSO.value]
                )
                mensaje += f"Se cancelaron {cant_recurso} liquidaciones con recurso. "
            else:
                mensaje += f"Saldo insuficiente (${saldo_anticipos:.2f}) para cancelar liquidaciones con recurso (${deuda_proceso_recurso:.2f}). "

        if deuda_proceso_sin_recurso > 0:
            tipos_sin_recurso = [t.value for t in TipoLiquidacionEnum if t.value != TipoLiquidacionEnum.RECURSO.value]
            df, _, cant_sin_recurso = sm.canceled_settlements(
                fecha_pago=data.fecha_pago,
                amount=0,
                proceso_id=proceso_id,
                tipos_liquidacion=tipos_sin_recurso
            )
            mensaje += f"Se cancelaron {cant_sin_recurso} liquidaciones sin recurso. "

        pendientes = db.query(LiquidacionCuotaCedida).filter(
            LiquidacionCuotaCedida.proceso_id == proceso_id,
            LiquidacionCuotaCedida.cancelada == False
        ).count()
        
        if pendientes == 0:
            proceso.estado = EstadoProcesoEnum.COMPLETADO
            
        db.commit()
        return {"status": "success", "message": mensaje.strip()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/procesos/{proceso_id}")
def delete_proceso(proceso_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso, Cobranza
    proceso = db.query(Proceso).options(joinedload(Proceso.cobranzas).joinedload(Cobranza.liquidaciones)).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
        
    from src.database.models.cobranzas import TipoProcesoEnum, LiquidacionCuotaCedida, EstadoProcesoEnum
    
    if proceso.estado == EstadoProcesoEnum.COMPLETADO:
        raise HTTPException(status_code=400, detail="No se puede eliminar un proceso que ya está COMPLETADO.")

    is_liquidacion = proceso.tipo in [TipoProcesoEnum.LIQUIDACIONES_MASIVAS, TipoProcesoEnum.LIQUIDACIONES_INDIVIDUALES]

    if not is_liquidacion:
        # Check if any cobranza has liquidaciones associated
        has_liquidaciones = any(len(cobranza.liquidaciones) > 0 for cobranza in proceso.cobranzas)
        if has_liquidaciones:
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar el proceso porque tiene liquidaciones asociadas a sus cobranzas."
            )
        
    try:
        from src.database.models.creditos import TipoCredito
        from src.database.models.cobranzas import TipoCobranzaEnum
        
        if is_liquidacion:
            db.query(LiquidacionCuotaCedida).filter(LiquidacionCuotaCedida.proceso_id == proceso_id).delete(synchronize_session=False)
            db.delete(proceso)
        else:
            penalty_credits = []
            affected_cuotas = set()
            for c in proceso.cobranzas:
                if c.cuota:
                    affected_cuotas.add(c.cuota)
                if c.tipo_cobranza == TipoCobranzaEnum.PENALTY:
                    if c.cuota and c.cuota.credito and c.cuota.credito.tipo_credito == TipoCredito.PENALTY:
                        penalty_credits.append(c.cuota.credito)
                        
            db.delete(proceso)
            for pc in penalty_credits:
                db.delete(pc)
            
            db.flush()
            
            from datetime import date
            hoy = date.today()
            for cuota in affected_cuotas:
                db.expire(cuota, ['cobranzas', 'liquidaciones'])
                cuota.actualizar_estado(hoy)
                if cuota.credito:
                    cuota.credito.actualizar_estado()
                    if cuota.credito.cliente:
                        cuota.credito.cliente.actualizar_estado()
                
        db.commit()
        return {"status": "success", "message": "Proceso eliminado exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando el proceso: {str(e)}")

@router.get("/cobranzas")
def get_cobranzas(
    skip: int = 0,
    limit: int = 50,
    proceso_id: Optional[str] = None,
    cuil: Optional[str] = None,
    credito_id: Optional[str] = None,
    id_cobranza: Optional[str] = None,
    tipo: Optional[str] = None,
    capital_min: Optional[float] = None,
    capital_max: Optional[float] = None,
    interes_min: Optional[float] = None,
    interes_max: Optional[float] = None,
    iva_min: Optional[float] = None,
    iva_max: Optional[float] = None,
    total_min: Optional[float] = None,
    total_max: Optional[float] = None,
    vto_dates: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from src.database.models.cobranzas import Cobranza
    from src.database.models import Cuota, Credito
    
    base_query = db.query(Cobranza).options(joinedload(Cobranza.cuota).joinedload(Cuota.credito))
    
    if proceso_id:
        base_query = base_query.filter(Cobranza.proceso_id == int(proceso_id))
    if id_cobranza:
        base_query = base_query.filter(Cobranza.id == int(id_cobranza))
    has_cuota_filters = bool(cuil or credito_id or vto_dates)
    if has_cuota_filters:
        base_query = base_query.outerjoin(Cuota)
        if credito_id:
            credito_id_list = [int(c.strip()) for c in credito_id.split(",") if c.strip().isdigit()]
            if credito_id_list:
                base_query = base_query.filter(Cuota.credito_id.in_(credito_id_list))
        if cuil:
            base_query = base_query.outerjoin(Credito, Cuota.credito_id == Credito.id).filter(Credito.cliente_cuil.like(f"%{cuil}%"))
            
    distinct_tipos = base_query.with_entities(Cobranza.tipo_cobranza).distinct().all()
    available_tipos = [t[0].value if hasattr(t[0], 'value') else str(t[0]) for t in distinct_tipos]

    vto_query = base_query
    if not has_cuota_filters:
        vto_query = vto_query.outerjoin(Cuota)
    distinct_vto = vto_query.with_entities(Cuota.fecha_vencimiento).filter(Cuota.fecha_vencimiento != None).distinct().all()
    available_vto_dates = [d[0].strftime("%Y-%m-%d") for d in distinct_vto if d[0]]

    query = base_query
    if tipo:
        tipo_list = [t.strip() for t in tipo.split(",")]
        query = query.filter(Cobranza.tipo_cobranza.in_(tipo_list))

    if vto_dates:
        from datetime import datetime
        vto_list_str = [d.strip() for d in vto_dates.split(",")]
        vto_list_date = []
        for d_str in vto_list_str:
            try:
                vto_list_date.append(datetime.strptime(d_str, "%Y-%m-%d").date())
            except ValueError:
                pass
        if vto_list_date:
            query = query.filter(Cuota.fecha_vencimiento.in_(vto_list_date))

    if capital_min is not None:
        query = query.filter(Cobranza.capital >= capital_min)
    if capital_max is not None:
        query = query.filter(Cobranza.capital <= capital_max)
        
    if interes_min is not None:
        query = query.filter(Cobranza.interes >= interes_min)
    if interes_max is not None:
        query = query.filter(Cobranza.interes <= interes_max)
        
    if iva_min is not None:
        query = query.filter(Cobranza.iva >= iva_min)
    if iva_max is not None:
        query = query.filter(Cobranza.iva <= iva_max)
        
    if total_min is not None or total_max is not None:
        total_expr = Cobranza.capital + Cobranza.interes + Cobranza.iva
        if total_min is not None:
            query = query.filter(total_expr >= total_min)
        if total_max is not None:
            query = query.filter(total_expr <= total_max)
            
    from sqlalchemy import func
    
    total = query.count()
    
    agg_query = query.with_entities(
        func.sum(Cobranza.capital).label("total_capital"),
        func.sum(Cobranza.interes).label("total_interes"),
        func.sum(Cobranza.iva).label("total_iva"),
        func.sum(Cobranza.capital + Cobranza.interes + Cobranza.iva).label("total_general")
    ).first()
    
    global_totals = {
        "capital": float(agg_query.total_capital or 0),
        "interes": float(agg_query.total_interes or 0),
        "iva": float(agg_query.total_iva or 0),
        "total": float(agg_query.total_general or 0)
    }

    cobranzas = query.order_by(desc(Cobranza.fecha)).offset(skip).limit(limit).all()
    
    result = []
    for c in cobranzas:
        cuota_nro = str(c.cuota.nro_cuota) if c.cuota else "-"
        cuota_vto = c.cuota.fecha_vencimiento.strftime("%Y-%m-%d") if c.cuota and c.cuota.fecha_vencimiento else "-"
        credito_id_str = str(c.cuota.credito_id) if c.cuota else "-"
        cliente_cuil_str = c.cuota.credito.cliente_cuil if c.cuota and c.cuota.credito else "-"
        
        result.append({
            "ID": c.id,
            "Proceso ID": str(c.proceso_id) if c.proceso_id else "-",
            "Fecha Emision": c.fecha.strftime("%Y-%m-%d") if c.fecha else "-",
            "Credito ID": credito_id_str,
            "Cliente CUIL": cliente_cuil_str,
            "Cuota Nro": cuota_nro,
            "Fecha Vencimiento": cuota_vto,
            "Tipo": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, 'value') else str(c.tipo_cobranza),
            "Capital": float(c.capital),
            "Interes": float(c.interes),
            "IVA": float(c.iva),
            "Total": float(c.capital + c.interes + c.iva)
        })
    return {"items": result, "total": total, "available_tipos": available_tipos, "available_vto_dates": available_vto_dates, "global_totals": global_totals}

@router.delete("/cobranzas/{cobranza_id}")
def delete_cobranza(cobranza_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    cobranza = db.query(Cobranza).filter(Cobranza.id == cobranza_id).first()
    if not cobranza:
        raise HTTPException(status_code=404, detail="Cobranza no encontrada")
        
    if len(cobranza.liquidaciones) > 0:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar la cobranza porque tiene liquidaciones asociadas."
        )
        
    cuota = cobranza.cuota
    credito = cuota.credito if cuota else None
    
    try:
        db.delete(cobranza)
        db.flush()
        
        from datetime import date
        hoy = date.today()
        if cuota:
            db.expire(cuota, ['cobranzas', 'liquidaciones'])
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            if credito.cliente:
                credito.cliente.actualizar_estado()
            
        db.commit()
        return {"status": "success", "message": "Cobranza eliminada exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando la cobranza: {str(e)}")

@router.put("/cobranzas/{cobranza_id}")
def modificar_cobranza(cobranza_id: int, datos: CobranzaIndividual, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    cobranza = db.query(Cobranza).filter(Cobranza.id == cobranza_id).first()
    if not cobranza:
        raise HTTPException(status_code=404, detail="Cobranza no encontrada")
        
    if len(cobranza.liquidaciones) > 0:
        raise HTTPException(
            status_code=400, 
            detail="No se puede modificar la cobranza porque tiene liquidaciones asociadas."
        )
        
    cuota = cobranza.cuota
    credito = cuota.credito if cuota else None
    
    try:
        db.delete(cobranza)
        db.flush()
        
        from datetime import date
        hoy = date.today()
        if cuota:
            db.expire(cuota, ['cobranzas', 'liquidaciones'])
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            if credito.cliente:
                credito.cliente.actualizar_estado()
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando la cobranza original: {str(e)}")
        
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(datos.fecha_pago, datetime.min.time()) if datos.fecha_pago else datetime.today()
        if datos.anticipada:
            df = manager.process_early_cancellation(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt
            )
        else:
            df = manager.process_standard_payment(
                identificador=datos.identificador,
                id_val=datos.id_val,
                amount=datos.monto,
                payment_date=fecha_pago_dt
            )
        
        if df.empty:
            raise ValueError("No se encontraron cuotas pendientes para el nuevo identificador proporcionado o la cobranza resultó vacía.")
            
        return {"status": "success", "message": "Cobranza modificada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


