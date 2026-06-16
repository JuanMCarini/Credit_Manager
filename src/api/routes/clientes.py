from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from src.database import get_db, Cliente
from src.api.schemas.clientes import ClienteCreate

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])

@router.post("")
async def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        nuevo_cliente = Cliente(**cliente_data.dict(exclude_unset=True))
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return {"status": "success", "message": "Cliente creado exitosamente", "cuil": nuevo_cliente.cuil}
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
    clientes = db.query(Cliente).all()
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
            "Estado": c.estado.value if c.estado else "-",
            "Fecha Estado": c.fecha_estado.strftime("%Y-%m-%d") if c.fecha_estado else "-",
            "Provincia": prov,
            "Empleador": emp,
            "Mail": c.mail or "-",
            "Teléfono": c.telefono or "-",
            "Fecha Ingreso": c.fecha_ingreso.strftime("%Y-%m-%d") if c.fecha_ingreso else "-",
            "Remuneración": float(c.remuneracion or 0.0)
        })
    return result

@router.get("/{cuil}")
def get_cliente(cuil: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(or_(Cliente.cuil == cuil, Cliente.documento == cuil)).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
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
        "empleador_id": cliente.empleador_id
    }

@router.get("/{cuil}/cuenta_corriente")
def get_cliente_cuenta_corriente(cuil: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.cuil == cuil).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    result = []
    for c in cliente.creditos:
        for cuota in c.cuotas:
            total_esperado = round(cuota.capital + cuota.interes + cuota.iva, 2)
            total_cobrado = 0.0
            detalle_cobranzas = []
            
            sorted_cobranzas = sorted(cuota.cobranzas, key=lambda cob: cob.fecha)
            for cob in sorted_cobranzas:
                tot = round(cob.capital + cob.interes + cob.iva, 2)
                total_cobrado += tot
                detalle_cobranzas.append({
                    "id": cob.id,
                    "fecha": cob.fecha.strftime("%d/%m/%Y"),
                    "tipo": cob.tipo_cobranza.value if hasattr(cob.tipo_cobranza, "value") else str(cob.tipo_cobranza),
                    "capital": round(cob.capital, 2),
                    "interes": round(cob.interes, 2),
                    "iva": round(cob.iva, 2),
                    "total": tot
                })
                
            total_cobrado = round(total_cobrado, 2)
            saldo = round(total_esperado - total_cobrado, 2)
            
            result.append({
                "credito_id": c.id,
                "id_externo": c.id_externo or "-",
                "nro_cuota": cuota.nro_cuota,
                "vencimiento": cuota.fecha_vencimiento.strftime("%d/%m/%Y"),
                "vencimiento_raw": cuota.fecha_vencimiento,
                "capital": round(cuota.capital, 2),
                "interes": round(cuota.interes, 2),
                "iva": round(cuota.iva, 2),
                "total_esperado": total_esperado,
                "total_cobrado": total_cobrado,
                "saldo_pendiente": saldo,
                "estado": cuota.estado.value,
                "detalle_cobranzas": detalle_cobranzas
            })
            
    result.sort(key=lambda x: (x["vencimiento_raw"], x["credito_id"], x["nro_cuota"]))
    
    for r in result:
        del r["vencimiento_raw"]
        
    return result

@router.put("/{cuil}")
async def update_cliente(
    cuil: str,
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        cliente = db.query(Cliente).filter(Cliente.cuil == cuil).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        update_data = cliente_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cliente, key, value)
            
        db.commit()
        db.refresh(cliente)
        return {"status": "success", "message": "Cliente actualizado exitosamente", "cuil": cliente.cuil}
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
