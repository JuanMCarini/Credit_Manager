from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from src.database import get_db
from src.logic.collections import CollectionManager
from src.api.schemas.cobranzas import CobranzaIndividual, CobranzaMasiva, ProcesoUpdate
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
        
        proceso_id = df.attrs.get("proceso_id") if hasattr(df, "attrs") else None
        
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

@router.get("/procesos")
def get_procesos(db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso
    procesos = db.query(Proceso).order_by(desc(Proceso.fecha_ejecucion)).all()
    result = []
    for p in procesos:
        result.append({
            "ID": p.id,
            "Tipo": p.tipo.value if hasattr(p.tipo, 'value') else str(p.tipo),
            "Estado": p.estado.value if hasattr(p.estado, 'value') else str(p.estado),
            "Descripción": p.descripcion or "-",
            "Fecha Ejecución": p.fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_ejecucion else "-"
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
        
        deuda_proceso = db.query(
            func.sum(LiquidacionCuotaCedida.capital + LiquidacionCuotaCedida.interes + LiquidacionCuotaCedida.iva)
        ).filter(
            LiquidacionCuotaCedida.proceso_id == proceso_id,
            LiquidacionCuotaCedida.cancelada == False,
            LiquidacionCuotaCedida.tipo_liquidacion == TipoLiquidacionEnum.RECURSO.value
        ).scalar() or 0.0
        deuda_proceso = float(deuda_proceso)
        
        mensaje = ""
        if data.monto > 0:
            mensaje += f"Se ingresó el pago de ${data.monto:.2f} a los anticipos. "
            
        if deuda_proceso == 0:
            proceso.estado = EstadoProcesoEnum.COMPLETADO
            db.commit()
            return {"status": "success", "message": mensaje + "El proceso no tiene deuda pendiente de cuotas con recurso."}

        if saldo_anticipos >= deuda_proceso:
            db.add(AnticiposSinAplicar(fecha=data.fecha_pago, socio_id=socio_id, monto=-deuda_proceso))
            
            sm = SettlementManager(db)
            df, _, cantidad_canceladas = sm.canceled_settlements(
                fecha_pago=data.fecha_pago,
                amount=0,
                proceso_id=proceso_id,
                tipos_liquidacion=[TipoLiquidacionEnum.RECURSO.value]
            )
            
            pendientes = db.query(LiquidacionCuotaCedida).filter(
                LiquidacionCuotaCedida.proceso_id == proceso_id,
                LiquidacionCuotaCedida.cancelada == False
            ).count()
            
            if pendientes == 0:
                proceso.estado = EstadoProcesoEnum.COMPLETADO
                
            mensaje += f"El saldo total (${saldo_anticipos:.2f}) cubrió la deuda de ${deuda_proceso:.2f}. Se cancelaron {cantidad_canceladas} liquidaciones con recurso."
        else:
            mensaje += f"El saldo total de anticipos (${saldo_anticipos:.2f}) no alcanza para cancelar el proceso completo (${deuda_proceso:.2f}). No se aplicaron pagos a liquidaciones."
            
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
            for c in proceso.cobranzas:
                if c.tipo_cobranza == TipoCobranzaEnum.PENALTY:
                    if c.cuota and c.cuota.credito and c.cuota.credito.tipo_credito == TipoCredito.PENALTY:
                        penalty_credits.append(c.cuota.credito)
                        
            db.delete(proceso)
            for pc in penalty_credits:
                db.delete(pc)
                
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
    db: Session = Depends(get_db)
):
    from src.database.models.cobranzas import Cobranza
    from src.database.models import Cuota, Credito
    
    base_query = db.query(Cobranza).options(joinedload(Cobranza.cuota).joinedload(Cuota.credito))
    
    if proceso_id:
        base_query = base_query.filter(Cobranza.proceso_id == int(proceso_id))
    if id_cobranza:
        base_query = base_query.filter(Cobranza.id == int(id_cobranza))
    if cuil or credito_id:
        base_query = base_query.join(Cuota)
        if credito_id:
            base_query = base_query.filter(Cuota.credito_id == int(credito_id))
        if cuil:
            base_query = base_query.join(Credito).filter(Credito.cliente_cuil.like(f"%{cuil}%"))
            
    # Calculate available types before applying the tipo filter
    distinct_tipos = base_query.with_entities(Cobranza.tipo_cobranza).distinct().all()
    available_tipos = [t[0].value if hasattr(t[0], 'value') else str(t[0]) for t in distinct_tipos]

    query = base_query
    if tipo:
        tipo_list = [t.strip() for t in tipo.split(",")]
        query = query.filter(Cobranza.tipo_cobranza.in_(tipo_list))
            
    total = query.count()
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
    return {"items": result, "total": total, "available_tipos": available_tipos}

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
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            
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
            cuota.actualizar_estado(hoy)
        if credito:
            credito.actualizar_estado()
            
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
        return {"status": "success", "message": "Cobranza modificada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


