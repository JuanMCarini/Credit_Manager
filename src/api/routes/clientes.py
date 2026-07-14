from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from src.database import get_db, Cliente, Credito, Cuota
from src.database.models.clientes import Referido
from src.api.schemas.clientes import ClienteCreate

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])

@router.post("")
def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        data = cliente_data.dict(exclude_unset=True)
        referidos_data = data.pop("referidos", [])
        nuevo_cliente = Cliente(**data)
        
        # Screening RePET automatizado
        from src.services.repet import screen_person, sync_repet_data
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        full_name = f"{nuevo_cliente.nombre} {nuevo_cliente.apellido}"
        try:
            asyncio.run(sync_repet_data(db))
            repet_result = screen_person(db, full_name=full_name)
            if repet_result.get("status") == "ALERT":
                nuevo_cliente.repet = True
        except Exception as e:
            logger.error(f"Error interno en screening RePET (alta cliente): {str(e)}")
            # Permitimos que continúe y se complete manualmente si hubo falla del servicio
        
        for ref in referidos_data:
            nuevo_cliente.referidos.append(Referido(**ref))
            
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return {"status": "success", "message": "Cliente creado exitosamente", "cuil": nuevo_cliente.cuil, "repet": nuevo_cliente.repet}
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()
        if "foreign key" in error_msg:
            raise HTTPException(status_code=400, detail="El ID de Provincia o Empleador ingresado no existe en la base de datos.")
        elif "unique" in error_msg:
            raise HTTPException(status_code=400, detail="Error de integridad. El CUIL o Documento ingresado ya está registrado.")
        else:
            raise HTTPException(status_code=400, detail=f"Error de base de datos: {str(e.orig)}")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def get_clientes_list(db: Session = Depends(get_db)):
    clientes = db.query(Cliente).options(
        joinedload(Cliente.provincia), 
        joinedload(Cliente.empleador)
    ).all()
    result = []
    for c in clientes:
        prov = c.provincia.nombre if c.provincia else "-"
        emp = c.empleador.razon_social if c.empleador else "-"
        result.append({
            "CUIL": c.cuil,
            "Documento": c.documento,
            "Apellido y Nombre": f"{c.apellido}, {c.nombre}" if c.apellido and c.nombre else (c.apellido or c.nombre),
            "Apellido": c.apellido or "-",
            "Nombre": c.nombre or "-",
            "Provincia": prov,
            "Empleador": emp,
            "PEP": "Sí" if c.pep else "No",
            "REPET": "Sí" if c.repet else "No",
            "Fecha Nacimiento": c.fecha_nacimiento.strftime("%Y-%m-%d") if c.fecha_nacimiento else "-",
            "Sexo": c.sexo.value if hasattr(c.sexo, "value") else (str(c.sexo) if c.sexo else "-"),
            "Estado Civil": c.estado_civil or "-",
            "Nacionalidad": c.nacionalidad or "-",
            "Legajo": c.legajo or "-",
            "Estado": c.estado.value if hasattr(c.estado, "value") else (str(c.estado) if c.estado else "-"),
            "Fecha Estado": c.fecha_estado.strftime("%Y-%m-%d") if c.fecha_estado else "-",
            "CBU": c.cbu or "-",
            "Provincia": prov,
            "Localidad": c.localidad or "-",
            "Código Postal": c.id_codigo_postal or "-",
            "Calle": c.calle or "-",
            "Calle Nro": c.calle_nro if c.calle_nro is not None else "-",
            "Piso": c.piso or "-",
            "Depto": c.depto or "-",
            "Empleador": emp,
            "Mail": c.mail or "-",
            "Teléfono": c.telefono or "-",
            "Teléfono 2": c.telefono_2 or "-",
            "Fecha Ingreso": c.fecha_ingreso.strftime("%Y-%m-%d") if c.fecha_ingreso else "-",
            "Remuneración": float(c.remuneracion or 0.0)
        })
    return result

@router.get("/{cuil}")
def get_cliente(cuil: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(or_(Cliente.cuil == cuil, Cliente.documento == cuil)).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    import asyncio
    from src.services.repet import screen_person, sync_repet_data
    try:
        asyncio.run(sync_repet_data(db))
        full_name = f"{cliente.nombre} {cliente.apellido}"
        repet_result = screen_person(db, full_name=full_name)
        if repet_result.get("status") == "ALERT" and not cliente.repet:
            cliente.repet = True
            db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error sincronizando RePET en get_cliente: {str(e)}")
    
    return {
        "cuil": cliente.cuil,
        "documento": cliente.documento,
        "apellido": cliente.apellido,
        "nombre": cliente.nombre,
        "fecha_nacimiento": cliente.fecha_nacimiento.strftime("%Y-%m-%d") if cliente.fecha_nacimiento else None,
        "sexo": cliente.sexo.value if cliente.sexo else None,
        "estado_civil": cliente.estado_civil,
        "nacionalidad": cliente.nacionalidad,
        "legajo": cliente.legajo,
        "estado": cliente.estado.value if cliente.estado else None,
        "cbu": cliente.cbu,
        "calle": cliente.calle,
        "calle_nro": cliente.calle_nro,
        "piso": cliente.piso,
        "depto": cliente.depto,
        "id_provincia": cliente.id_provincia,
        "id_codigo_postal": cliente.id_codigo_postal,
        "localidad": cliente.localidad,
        "telefono": cliente.telefono,
        "telefono_2": cliente.telefono_2,
        "mail": cliente.mail,
        "fecha_ingreso": cliente.fecha_ingreso.strftime("%Y-%m-%d") if cliente.fecha_ingreso else None,
        "remuneracion": float(cliente.remuneracion or 0.0),
        "empleador_id": cliente.empleador_id,
        "cargo": cliente.cargo,
        "pep": cliente.pep,
        "repet": cliente.repet,
        "referidos": [
            {
                "nombre": r.nombre,
                "apellido": r.apellido,
                "telefono": r.telefono,
                "email": r.email
            } for r in cliente.referidos
        ]
    }

@router.get("/{cuil}/bcra")
def get_cliente_bcra(cuil: str, db: Session = Depends(get_db)):
    """
    Consulta la situación actual del cliente en la Central de Deudores del BCRA.
    """
    from src.services.bcra import consultar_cuit_api
    import re
    
    # Limpiamos el CUIL para que sean solo números
    cuil_clean = re.sub(r"\D", "", cuil)
    
    respuesta = consultar_cuit_api(cuil_clean)
    
    if "Error" in respuesta and respuesta["Error"]:
        raise HTTPException(status_code=500, detail=f"Error consultando BCRA: {respuesta['Estado']}")
        
    return respuesta


@router.get("/{cuil}/cuenta_corriente")
def get_cliente_cuenta_corriente(cuil: str, db: Session = Depends(get_db)):
    import traceback
    try:
        cliente = db.query(Cliente).options(
            joinedload(Cliente.creditos).joinedload(Credito.cuotas).joinedload(Cuota.cobranzas)
        ).filter(Cliente.cuil == cuil).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        result = []
        from datetime import date
        for c in cliente.creditos:
            for cuota in c.cuotas:
                cuota_capital = float(cuota.capital or 0.0)
                cuota_interes = float(cuota.interes or 0.0)
                cuota_iva = float(cuota.iva or 0.0)
                total_esperado = round(cuota_capital + cuota_interes + cuota_iva, 2)
                total_cobrado = 0.0
                detalle_cobranzas = []
                
                sorted_cobranzas = sorted(cuota.cobranzas, key=lambda cob: cob.fecha if cob.fecha else date.min)
                for cob in sorted_cobranzas:
                    cob_capital = float(cob.capital or 0.0)
                    cob_interes = float(cob.interes or 0.0)
                    cob_iva = float(cob.iva or 0.0)
                    tot = round(cob_capital + cob_interes + cob_iva, 2)
                    total_cobrado += tot
                    detalle_cobranzas.append({
                        "id": cob.id,
                        "fecha": cob.fecha.strftime("%d/%m/%Y") if cob.fecha else "-",
                        "tipo": cob.tipo_cobranza.value if hasattr(cob.tipo_cobranza, "value") else str(cob.tipo_cobranza),
                        "capital": round(cob_capital, 2),
                        "interes": round(cob_interes, 2),
                        "iva": round(cob_iva, 2),
                        "total": tot
                    })
                    
                total_cobrado = round(total_cobrado, 2)
                saldo = round(total_esperado - total_cobrado, 2)
                
                result.append({
                    "credito_id": c.id,
                    "id_externo": c.id_externo or "-",
                    "nro_cuota": cuota.nro_cuota,
                    "vencimiento": cuota.fecha_vencimiento.strftime("%d/%m/%Y") if cuota.fecha_vencimiento else "-",
                    "vencimiento_raw": cuota.fecha_vencimiento or date.min,
                    "capital": round(cuota_capital, 2),
                    "interes": round(cuota_interes, 2),
                    "iva": round(cuota_iva, 2),
                    "total_esperado": total_esperado,
                    "total_cobrado": total_cobrado,
                    "saldo_pendiente": saldo,
                    "estado": cuota.estado.value if hasattr(cuota.estado, "value") else str(cuota.estado) if cuota.estado else "-",
                    "detalle_cobranzas": detalle_cobranzas
                })
                
        result.sort(key=lambda x: (str(x["vencimiento_raw"]), x["credito_id"], x["nro_cuota"]))
        
        for r in result:
            del r["vencimiento_raw"]
            
        from fastapi.encoders import jsonable_encoder
        json_compatible_item_data = jsonable_encoder(result)
        return json_compatible_item_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error traceback: {traceback.format_exc()}")

@router.put("/{cuil}")
def update_cliente(
    cuil: str,
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        cliente = db.query(Cliente).filter(Cliente.cuil == cuil).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        update_data = cliente_data.dict(exclude_unset=True)
        referidos_data = update_data.pop("referidos", None)
        
        for key, value in update_data.items():
            setattr(cliente, key, value)
            
        import asyncio
        from src.services.repet import screen_person, sync_repet_data
        try:
            asyncio.run(sync_repet_data(db))
            full_name = f"{cliente.nombre} {cliente.apellido}"
            repet_result = screen_person(db, full_name=full_name)
            if repet_result.get("status") == "ALERT":
                cliente.repet = True
            else:
                # Si queremos permitir limpiar la bandera si no sale más en el listado
                # cliente.repet = False
                pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error sincronizando RePET en update_cliente: {str(e)}")
            
        if referidos_data is not None:
            cliente.referidos = [Referido(**ref) for ref in referidos_data]
            
        db.commit()
        db.refresh(cliente)
        return {"status": "success", "message": "Cliente actualizado exitosamente", "cuil": cliente.cuil, "repet": cliente.repet}
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()
        if "foreign key" in error_msg:
            raise HTTPException(status_code=400, detail="El ID de Provincia o Empleador ingresado no existe en la base de datos.")
        elif "unique" in error_msg:
            raise HTTPException(status_code=400, detail="Error de integridad. El CUIL o Documento ingresado ya está registrado por otro cliente.")
        else:
            raise HTTPException(status_code=400, detail=f"Error de base de datos: {str(e.orig)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{cuil}")
def delete_cliente(cuil: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.cuil == cuil).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    # Chequear manualmente si tiene créditos para evitar errores de SQLAlchemy de Foreign Keys nulos
    has_credits = db.query(Credito).filter(Credito.cliente_cuil == cuil).first()
    if has_credits:
        raise HTTPException(status_code=400, detail="No se puede borrar este cliente porque ya tiene préstamos o cuotas asociadas en el historial.")
        
    try:
        db.delete(cliente)
        db.commit()
        return {"status": "success", "message": "Cliente eliminado exitosamente"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se puede borrar este cliente porque ya tiene préstamos o cuotas asociadas en el historial.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error inesperado al borrar el cliente: {str(e)}")
