"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, asc, desc, cast, String
import math

from src.database import get_db, Cliente, SexoEnum, EstadoClienteEnum, Provincia, Empleador, SocioComercial, Credito, TipoCredito, TasaYComision, Cartera, Relacion

from src.logic.origination import LoanOriginator
from src.logic.amortization import AmortizationEngine
from src.logic.collections import CollectionManager
from src.reports.balances import saldos
from src.portfolio.sell import PortfolioSell

# Variables for sync optimization
_LAST_SYNC_DATE = None
_LAST_SYNC_STATE_HASH = None

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
app = FastAPI(
    title="Credit Manager Core Engine API",
    description="API RESTful para interactuar con el motor financiero de gestión de cartera de créditos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Endpoint de prueba de estado (health check).
    Retorna 200 OK y el estado general de la aplicación.
    """
    return {"status": "ok", "message": "Credit Manager API is running"}


@app.get("/simular-cuotas", tags=["Amortización"])
async def simular_cuotas(
    credito_id: int = Query(..., description="ID identificador del crédito de simulación"),
    capital: float = Query(..., description="Monto de capital a amortizar"),
    tna_c_iva: float = Query(..., description="Tasa Nominal Anual con IVA incluido"),
    plazo: int = Query(..., description="Cantidad de meses/cuotas del crédito"),
    fecha_emision: date = Query(..., description="Fecha de emisión del crédito (YYYY-MM-DD)"),
    dia_vencimiento: int = Query(28, description="Día del mes para el vencimiento"),
    gracia: int = Query(2, description="Meses de gracia aplicables"),
    tasa_iva: float = Query(0.21, description="Alícuota impositiva (ej. 0.21)"),
    dia_corte: int = Query(28, description="Día de corte del crédito"),
) -> List[Dict[str, Any]]:
    """
    Genera el cronograma de pagos utilizando el Sistema Francés, aplicando 
    la lógica matemática y redondeos precisos del core engine.
    """
    try:
        # Invoca al core engine sin modificar lógica interna
        cuotas_obj = AmortizationEngine.generate_french_schedule(
            credito_id=credito_id,
            capital=capital,
            tna_c_iva=tna_c_iva,
            plazo=plazo,
            fecha_emision=fecha_emision,
            dia_vencimiento=dia_vencimiento,
            gracia=gracia,
            tasa_iva=tasa_iva,
            dia_corte=dia_corte,
        )

        # Serialización de los objetos Cuota retornados
        return [
            {
                "credito_id": c.credito_id,
                "nro_cuota": c.nro_cuota,
                "fecha_vencimiento": c.fecha_vencimiento.strftime("%Y-%m-%d") if c.fecha_vencimiento else None,
                "capital": c.capital,
                "interes": c.interes,
                "iva": c.iva,
            }
            for c in cuotas_obj
        ]
    except ValueError as ve:
        # Excepciones controladas por el motor (ej. diferencias de centavos)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Error general interno
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/api/v1/reports/balances", tags=["Reportes"])
async def get_saldos(
    fecha: Optional[datetime] = Query(None, description="Fecha de corte para el cálculo. Por defecto es hoy."),
    con_saldo: bool = Query(True, description="Filtra solo las operaciones que aún mantienen saldo deudor."),
    propias: Optional[bool] = Query(None, description="Verdadero para cartera propia, Falso para terceros, Nulo para ambas."),
    agrupar: bool = Query(False, description="Activa el pipeline de agrupación dinámico."),
    clientes: bool = Query(False, description="Agrupa y totaliza saldos por cliente."),
    carteras: bool = Query(False, description="Agrupa y totaliza saldos por cartera."),
    socios: bool = Query(False, description="Agrupa y totaliza saldos por socio."),
    originador: bool = Query(False, description="Agrupa y totaliza saldos por socio originador."),
    vencimientos: bool = Query(False, description="Agrupa y totaliza saldos por fecha de vencimiento."),
    dueño: bool = Query(False, description="Agrupa y totaliza saldos por dueño de la cartera."),
    recurso: bool = Query(False, description="Agrupa y totaliza saldos diferenciando si tienen recurso."),
    iva: bool = Query(False, description="Agrupa y totaliza saldos por IVA."),
) -> List[Dict[str, Any]]:
    """
    Expone la generación del reporte de saldos. Devuelve los registros crudos o 
    agrupados desde el core engine, mapeados como una estructura JSON-friendly.
    """
    try:
        # Generar el DataFrame desde src.reports.balances
        df = saldos(
            fecha=fecha,
            con_saldo=con_saldo,
            propias=propias,
            agrupar=agrupar,
            clientes=clientes,
            carteras=carteras,
            socios=socios,
            originador=originador,
            vencimientos=vencimientos,
            dueño=dueño,
            recurso=recurso,
            iva=iva,
        )

        # El DataFrame de saldos (agrupado o no) utiliza el índice para almacenar 
        # información vital (como el MultiIndex de agrupaciones o [ID Credito, Nro. Cuota]).
        # Lo reseteamos siempre para que formen parte de las columnas exportadas en JSON.
        df = df.reset_index()

        # Reemplazar NaNs o NaTs con valores null (None en Python) compatibles con JSON
        df = df.replace({np.nan: None})

        # Convertir atributos Datetime de Pandas a strings para serialización JSON exitosa
        for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")

        # Retornar una lista de diccionarios (equivalente al array JSON de objetos)
        return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la generación del reporte: {str(e)}")

import io
from fastapi.responses import StreamingResponse

@app.get("/api/v1/reports/balances/excel", tags=["Reportes"])
async def export_saldos_excel(
    fecha: Optional[datetime] = Query(None, description="Fecha de corte para el cálculo. Por defecto es hoy."),
    con_saldo: bool = Query(True, description="Filtra solo las operaciones que aún mantienen saldo deudor."),
    propias: Optional[bool] = Query(None, description="Verdadero para cartera propia, Falso para terceros, Nulo para ambas."),
    agrupar: bool = Query(False, description="Activa el pipeline de agrupación dinámico."),
    clientes: bool = Query(False, description="Agrupa y totaliza saldos por cliente."),
    carteras: bool = Query(False, description="Agrupa y totaliza saldos por cartera."),
    socios: bool = Query(False, description="Agrupa y totaliza saldos por socio."),
    originador: bool = Query(False, description="Agrupa y totaliza saldos por socio originador."),
    vencimientos: bool = Query(False, description="Agrupa y totaliza saldos por fecha de vencimiento."),
    dueño: bool = Query(False, description="Agrupa y totaliza saldos por dueño de la cartera."),
    recurso: bool = Query(False, description="Agrupa y totaliza saldos diferenciando si tienen recurso."),
    iva: bool = Query(False, description="Agrupa y totaliza saldos por IVA."),
):
    try:
        df = saldos(
            fecha=fecha, con_saldo=con_saldo, propias=propias, agrupar=agrupar,
            clientes=clientes, carteras=carteras, socios=socios, originador=originador,
            vencimientos=vencimientos, dueño=dueño, recurso=recurso, iva=iva
        )
        df = df.reset_index()

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Saldos')
        output.seek(0)

        headers = {'Content-Disposition': 'attachment; filename="reporte_saldos.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")



# -------------------------------------------------------------------
# Modelos Pydantic
# -------------------------------------------------------------------
class ClienteCreate(BaseModel):
    cuil: str = Field(..., max_length=11, description="CUIL sin guiones (11 dígitos)")
    documento: str = Field(..., max_length=10)
    apellido: str = Field(..., max_length=100)
    nombre: str = Field(..., max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    estado_civil: Optional[str] = None
    nacionalidad: Optional[str] = None
    legajo: Optional[str] = None
    estado: Optional[EstadoClienteEnum] = EstadoClienteEnum.ACTIVO
    cbu: Optional[str] = None
    calle: Optional[str] = None
    calle_nro: Optional[int] = None
    piso: Optional[str] = None
    depto: Optional[str] = None
    id_provincia: Optional[int] = None
    id_codigo_postal: Optional[str] = None
    localidad: Optional[str] = None
    telefono: Optional[str] = None
    telefono_2: Optional[str] = None
    mail: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    remuneracion: float = 0.0
    empleador_id: Optional[int] = None

class CreditoCreate(BaseModel):
    cliente_cuil: str
    capital: float
    tna_c_iva: float
    plazo: int
    socio_originador_id: Optional[int] = None
    comision_id: Optional[int] = None
    fecha_emision: Optional[date] = None
    dia_vencimiento: int = 28
    tipo_credito: TipoCredito = TipoCredito.FRANCES

@app.post("/api/v1/clientes", tags=["Clientes"])
async def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Endpoint para crear un nuevo cliente en la base de datos.
    """
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

@app.post("/api/v1/creditos/originacion", tags=["Créditos"])
async def create_credito(
    credito_data: CreditoCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Endpoint para originar un nuevo crédito para un cliente existente.
    Genera automáticamente el crédito y sus cuotas (plan de amortización).
    """
    try:
        originator = LoanOriginator(db_session=db)
        nuevo_credito = originator.originate(
            client_cuil=credito_data.cliente_cuil,
            capital=credito_data.capital,
            tna_c_iva=credito_data.tna_c_iva,
            term=credito_data.plazo,
            partner_id=credito_data.socio_originador_id,
            issuance_date=credito_data.fecha_emision,
            due_day=credito_data.dia_vencimiento,
            type=credito_data.tipo_credito,
            comision_id=credito_data.comision_id
        )
        return {
            "status": "success",
            "message": "Crédito originado y cuotas generadas exitosamente.",
            "credito_id": nuevo_credito.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error originando el crédito: {str(e)}")


@app.get("/api/v1/clientes", tags=["Clientes"])
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

@app.get("/api/v1/clientes/{cuil}", tags=["Clientes"])
def get_cliente(cuil: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(or_(Cliente.cuil == cuil, Cliente.documento == cuil)).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # We serialize the full SQLAlchemy object
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

@app.get("/api/v1/clientes/{cuil}/cuenta_corriente", tags=["Clientes"])
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
            
            # Ordenar cobranzas por fecha
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
                "vencimiento_raw": cuota.fecha_vencimiento,  # Para ordenamiento
                "capital": round(cuota.capital, 2),
                "interes": round(cuota.interes, 2),
                "iva": round(cuota.iva, 2),
                "total_esperado": total_esperado,
                "total_cobrado": total_cobrado,
                "saldo_pendiente": saldo,
                "estado": cuota.estado.value,
                "detalle_cobranzas": detalle_cobranzas
            })
            
    # Ordenar todas las cuotas cronológicamente por vencimiento, luego por credito_id y nro_cuota
    result.sort(key=lambda x: (x["vencimiento_raw"], x["credito_id"], x["nro_cuota"]))
    
    # Remover vencimiento_raw antes de retornar
    for r in result:
        del r["vencimiento_raw"]
        
    return result

@app.put("/api/v1/clientes/{cuil}", tags=["Clientes"])
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

@app.delete("/api/v1/clientes/{cuil}", tags=["Clientes"])
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

# -------------------------------------------------------------------
# Créditos Endpoints
# -------------------------------------------------------------------

class CreditoEstadoUpdate(BaseModel):
    estado: str

@app.patch("/api/v1/creditos/{credito_id}/estado", tags=["Creditos"])
def update_credito_estado(credito_id: int, data: CreditoEstadoUpdate, db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    
    from src.database.models import EstadoCredito
    try:
        nuevo_estado = EstadoCredito(data.estado.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido.")
        
    credito.estado = nuevo_estado
    db.commit()
    return {"status": "success", "message": "Estado actualizado"}

@app.get("/api/v1/creditos/{credito_id}/cuotas", tags=["Creditos"])
def get_credito_cuotas(credito_id: int, db: Session = Depends(get_db)):
    from src.database.models import Cuota
    cuotas = db.query(Cuota).filter(Cuota.credito_id == credito_id).order_by(Cuota.nro_cuota).all()
    
    result = []
    for c in cuotas:
        total_esperado = round(c.capital + c.interes + c.iva, 2)
        
        total_cobrado = 0.0
        detalle_cobranzas = []
        
        # Sort collections by date
        sorted_cobranzas = sorted(c.cobranzas, key=lambda cob: cob.fecha)
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
            "nro_cuota": c.nro_cuota,
            "vencimiento": c.fecha_vencimiento.strftime("%d/%m/%Y"),
            "capital": round(c.capital, 2),
            "interes": round(c.interes, 2),
            "iva": round(c.iva, 2),
            "total_esperado": total_esperado,
            "total_cobrado": total_cobrado,
            "saldo_pendiente": saldo,
            "estado": c.estado.value,
            "detalle_cobranzas": detalle_cobranzas
        })
        
    return result

@app.get("/api/v1/creditos", tags=["Creditos"])
def get_creditos_list(db: Session = Depends(get_db)):
    creditos = db.query(Credito).all()
    result = []
    for c in creditos:
        nombre_cliente = f"{c.cliente.apellido}, {c.cliente.nombre}" if c.cliente else "-"
        origen = c.origen.value if hasattr(c.origen, 'value') else str(c.origen)
        socio = c.socio_originador.razon_social if c.socio_originador else "-"
        result.append({
            "ID": c.id,
            "ID Externo": c.id_externo or "-",
            "Cliente CUIL": c.cliente_cuil,
            "Cliente Nombre": nombre_cliente,
            "Origen": origen,
            "Socio Originador": socio,
            "Capital": float(c.capital),
            "TNA con IVA": float(c.tna_c_iva),
            "Plazo": c.plazo,
            "Fecha Emisión": c.fecha_emision.strftime("%Y-%m-%d"),
            "Estado": c.estado.value if c.estado else "-",
            "Tipo Crédito": c.tipo_credito.value if c.tipo_credito else "-",
            "Día Vto": c.dia_vencimiento
        })
    return result

@app.delete("/api/v1/creditos/{credito_id}", tags=["Creditos"])
def delete_credito(credito_id: int, db: Session = Depends(get_db)):
    credito = db.query(Credito).filter(Credito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
        
    from src.database.models import EstadoCredito
    if credito.estado != EstadoCredito.APROBADO:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede eliminar un crédito si su estado es APROBADO."
        )
        
    # Check if there are any cobranzas associated with this credit's cuotas
    has_cobranzas = any(len(cuota.cobranzas) > 0 for cuota in credito.cuotas)
    if has_cobranzas:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar el crédito porque ya tiene cobranzas asociadas."
        )
        
    try:
        db.delete(credito)
        db.commit()
        return {"status": "success", "message": "Crédito eliminado exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando el crédito: {str(e)}")

# -------------------------------------------------------------------
# Cobranzas Endpoints
# -------------------------------------------------------------------

class CobranzaIndividual(BaseModel):
    identificador: str
    id_val: str
    monto: float
    fecha_pago: Optional[date] = None
    anticipada: bool = False

class CobranzaMasiva(BaseModel):
    identificador: str
    id_val: str
    cuotas: List[int]
    monto_total: float
    fecha_pago: Optional[date] = None

class VentaCarteraRequest(BaseModel):
    nombre_cartera: str
    fecha_venta: date
    tna_descuento: float
    cuit_comprador: str
    razon_social_comprador: str
    mora: bool = False
    recurso: bool = True
    iva: bool = False
    fecha_emision_desde: Optional[date] = None
    fecha_emision_hasta: Optional[date] = None
    fecha_vencimiento_desde: Optional[date] = None
    fecha_vencimiento_hasta: Optional[date] = None
    creditos_excluidos: List[int] = Field(default_factory=list)
    cartera_id: Optional[int] = None
    usar_cuotas_guardadas: bool = False

class UpdateCarteraRequest(BaseModel):
    fecha_compra: Optional[date] = None
    tna_descuento: Optional[float] = None
    recurso: Optional[bool] = None
    iva: Optional[bool] = None
    estado: Optional[str] = None

@app.post("/api/v1/cobranzas/individual", tags=["Cobranzas"])
def procesar_cobranza_individual(
    datos: CobranzaIndividual,
    db: Session = Depends(get_db)
):
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
        return {"status": "success", "message": "Cobranza individual procesada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/cobranzas/masiva", tags=["Cobranzas"])
async def procesar_cobranza_masiva(
    identificador: str = Form(...),
    id_column: str = Form("A"),
    amount_column: str = Form("B"),
    fecha_pago: Optional[date] = Form(None),
    anticipada: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    manager = CollectionManager(db)
    try:
        fecha_pago_dt = datetime.combine(fecha_pago, datetime.min.time()) if fecha_pago else datetime.today()
        file_bytes = await file.read()
        
        df = manager.process_massive_collection(
            identificador=identificador,
            id_column=id_column,
            amount_column=amount_column,
            payment_date=fecha_pago_dt,
            early=anticipada,
            file_bytes=file_bytes,
            filename=file.filename
        )
        return {"status": "success", "message": "Cobranza masiva procesada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -------------------------------------------------------------------
# Tablas Auxiliares
# -------------------------------------------------------------------

AUX_TABLES = {
    "provincias": Provincia,
    "empleadores": Empleador,
    "socios": SocioComercial,
    "tasas_y_comisiones": TasaYComision,
    "relaciones": Relacion
}

class TabulatorSort(BaseModel):
    field: str
    dir: str

class TabulatorFilter(BaseModel):
    field: str
    type: str
    value: Any

class TabulatorRequest(BaseModel):
    page: int = 1
    size: int = 50
    sort: Optional[List[TabulatorSort]] = []
    filter: Optional[List[TabulatorFilter]] = []

@app.post("/api/v1/auxiliares/{tabla}/data", tags=["Auxiliares"])
def get_aux_table_data(tabla: str, request: TabulatorRequest, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    model = AUX_TABLES[tabla]
    query = db.query(model)

    # 1. Apply Filters
    if request.filter:
        for f in request.filter:
            if not hasattr(model, f.field):
                continue
            column = getattr(model, f.field)
            
            # Simple operators mapping
            if f.type == "like":
                query = query.filter(cast(column, String).ilike(f"%{f.value}%"))
            elif f.type == "=":
                query = query.filter(column == f.value)
            elif f.type == "!=":
                query = query.filter(column != f.value)
            elif f.type == ">":
                query = query.filter(column > f.value)
            elif f.type == "<":
                query = query.filter(column < f.value)
            elif f.type == ">=":
                query = query.filter(column >= f.value)
            elif f.type == "<=":
                query = query.filter(column <= f.value)
    
    # 2. Count total rows after filtering
    total_count = query.count()
    last_page = math.ceil(total_count / request.size) if request.size > 0 else 1

    # 3. Apply Sorting
    if request.sort:
        for s in request.sort:
            if not hasattr(model, s.field):
                continue
            column = getattr(model, s.field)
            if s.dir == "asc":
                query = query.order_by(asc(column))
            elif s.dir == "desc":
                query = query.order_by(desc(column))

    # 4. Apply Pagination
    query = query.offset((request.page - 1) * request.size).limit(request.size)
    records = query.all()

    data = [
        {c.name: getattr(r, c.name) for c in model.__table__.columns}
        for r in records
    ]

    return {
        "last_page": last_page,
        "data": data
    }


@app.get("/api/v1/auxiliares/{tabla}", tags=["Auxiliares"])
def get_aux_table(tabla: str, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    model = AUX_TABLES[tabla]
    records = db.query(model).all()
    # Convert SQLAlchemy objects to dict
    return [
        {c.name: getattr(r, c.name) for c in model.__table__.columns}
        for r in records
    ]

def _parse_aux_payload(payload: dict) -> dict:
    parsed = {}
    from datetime import datetime
    for k, v in payload.items():
        if isinstance(v, str):
            try:
                if len(v) == 10 and v[4] == '-' and v[7] == '-':
                    parsed[k] = datetime.strptime(v, "%Y-%m-%d").date()
                    continue
            except ValueError:
                pass
        parsed[k] = v
    return parsed

@app.post("/api/v1/auxiliares/{tabla}", tags=["Auxiliares"])
def create_aux_record(tabla: str, payload: dict, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    payload = _parse_aux_payload(payload)
    try:
        if tabla == "socios":
            nuevo = SocioComercial.create_socio(db=db, **payload)
        else:
            model = AUX_TABLES[tabla]
            nuevo = model(**payload)
            db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return {"status": "success", "id": getattr(nuevo, "id", None)}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Los datos ingresados no son válidos (Verifique que los números y las fechas tengan el formato correcto).")
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad: Ya existe un registro con esos datos únicos.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/auxiliares/{tabla}/{record_id}", tags=["Auxiliares"])
def update_aux_record(tabla: str, record_id: int, payload: dict, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    model = AUX_TABLES[tabla]
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    
    payload = _parse_aux_payload(payload)
    try:
        for key, value in payload.items():
            if hasattr(record, key) and key != "id":
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return {"status": "success", "id": record.id}
    except TypeError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Los datos ingresados no son válidos (Verifique que los números y las fechas tengan el formato correcto).")
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar: Datos duplicados u otro conflicto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/auxiliares/{tabla}/{record_id}", tags=["Auxiliares"])
def delete_aux_record(tabla: str, record_id: int, db: Session = Depends(get_db)):
    if tabla not in AUX_TABLES:
        raise HTTPException(status_code=404, detail="Tabla auxiliar no encontrada.")
    
    model = AUX_TABLES[tabla]
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    
    try:
        db.delete(record)
        db.commit()
        return {"status": "success", "message": "Registro eliminado exitosamente."}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar este registro porque está siendo utilizado por otros registros en el sistema (restricción de integridad referencial)."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# System Actions
# -------------------------------------------------------------------

@app.post("/api/v1/system/sync-states", tags=["System"])
@app.post("/api/v1/system/actualizar_estados", tags=["System"])
def sync_system_states(db: Session = Depends(get_db)):
    global _LAST_SYNC_DATE, _LAST_SYNC_STATE_HASH
    from src.database.models import Cuota, Credito, Cliente, EstadoCredito, EstadoClienteEnum, Cobranza
    from sqlalchemy import func
    from datetime import date
    hoy = date.today()

    try:
        # Optimization: Bypass sync if no new credits/collections and day hasn't changed
        credito_stats = db.query(func.max(Credito.id), func.count(Credito.id)).first()
        cobranza_stats = db.query(func.max(Cobranza.id), func.count(Cobranza.id)).first()
        current_state_hash = f"cred:{credito_stats[0]}-{credito_stats[1]}_cob:{cobranza_stats[0]}-{cobranza_stats[1]}"
        
        if _LAST_SYNC_DATE == hoy and _LAST_SYNC_STATE_HASH == current_state_hash:
            return {"status": "success", "message": "Estados ya se encontraban sincronizados."}

        # 1. Update Cuotas
        cuotas = db.query(Cuota).all()
        for c in cuotas:
            c.actualizar_estado(hoy)

        # 2. Update Creditos
        creditos = db.query(Credito).all()
        for cred in creditos:
            if cred.fecha_emision == hoy:
                continue
            cred.actualizar_estado()
        
        # 3. Update Clientes
        clientes = db.query(Cliente).all()
        for cli in clientes:
            creditos_cli = cli.creditos
            if not creditos_cli:
                # If no credits, keep as INACTIVO or default
                cli.estado = EstadoClienteEnum.INACTIVO
                continue
            
            # Extract current states of their credits
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
                # Check if all are cancelled
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

# -------------------------------------------------------------------
# Cobranzas y Procesos
# -------------------------------------------------------------------

@app.get("/api/v1/procesos", tags=["Cobranzas"])
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

class ProcesoUpdate(BaseModel):
    estado: str
    descripcion: Optional[str] = None

@app.put("/api/v1/procesos/{proceso_id}", tags=["Cobranzas"])
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

@app.delete("/api/v1/procesos/{proceso_id}", tags=["Cobranzas"])
def delete_proceso(proceso_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Proceso
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
        
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
        
        penalty_credits = []
        for c in proceso.cobranzas:
            if c.tipo_cobranza == TipoCobranzaEnum.PENALTY:
                if c.cuota and c.cuota.credito and c.cuota.credito.tipo_credito == TipoCredito.PENALTY:
                    penalty_credits.append(c.cuota.credito)
                    
        db.delete(proceso)
        for pc in penalty_credits:
            db.delete(pc)
            
        db.commit()
        return {"status": "success", "message": "Proceso y sus cobranzas eliminados exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando el proceso: {str(e)}")

@app.get("/api/v1/cobranzas", tags=["Cobranzas"])
def get_cobranzas(db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    # Para evitar bloqueos con mucha data, leemos un máximo en memoria o aplicamos limit.
    # Siguiendo el diseño actual sin paginación, usaremos limit 5000 por seguridad.
    cobranzas = db.query(Cobranza).order_by(desc(Cobranza.fecha)).limit(5000).all()
    result = []
    for c in cobranzas:
        cuota_nro = c.cuota.nro_cuota if c.cuota else "-"
        cuota_vto = c.cuota.fecha_vencimiento.strftime("%Y-%m-%d") if c.cuota and c.cuota.fecha_vencimiento else "-"
        credito_id = c.cuota.credito_id if c.cuota else "-"
        cliente_cuil = c.cuota.credito.cliente_cuil if c.cuota and c.cuota.credito else "-"
        
        result.append({
            "ID": c.id,
            "Proceso ID": c.proceso_id or "-",
            "Fecha Emisión": c.fecha.strftime("%Y-%m-%d") if c.fecha else "-",
            "Crédito ID": credito_id,
            "Cliente CUIL": cliente_cuil,
            "Cuota Nro": cuota_nro,
            "Fecha Vencimiento": cuota_vto,
            "Tipo": c.tipo_cobranza.value if hasattr(c.tipo_cobranza, 'value') else str(c.tipo_cobranza),
            "Capital": float(c.capital),
            "Interés": float(c.interes),
            "IVA": float(c.iva),
            "Total": float(c.capital + c.interes + c.iva)
        })
    return result

@app.delete("/api/v1/cobranzas/{cobranza_id}", tags=["Cobranzas"])
def delete_cobranza(cobranza_id: int, db: Session = Depends(get_db)):
    from src.database.models.cobranzas import Cobranza
    cobranza = db.query(Cobranza).filter(Cobranza.id == cobranza_id).first()
    if not cobranza:
        raise HTTPException(status_code=404, detail="Cobranza no encontrada")
        
    # Check if the cobranza has liquidaciones associated
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

@app.put("/api/v1/cobranzas/{cobranza_id}", tags=["Cobranzas"])
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
        # Borrar la cobranza vieja
        db.delete(cobranza)
        db.flush()
        
        # Actualizar estado de cuota y credito antes de aplicar el nuevo cobro
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
        
    # Procesar la nueva cobranza con los datos proporcionados
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

# -------------------------------------------------------------------
# Operaciones de Cartera
# -------------------------------------------------------------------

@app.get("/api/v1/carteras", tags=["Carteras"])
def get_carteras(db: Session = Depends(get_db)):
    from src.database.models import Cartera, SocioComercial
    carteras = db.query(Cartera).join(SocioComercial, Cartera.socio_id == SocioComercial.id).all()
    
    result = []
    for c in carteras:
        result.append({
            "id": c.id,
            "nombre": c.nombre,
            "tipo_operacion": c.tipo_operacion.value if hasattr(c.tipo_operacion, 'value') else c.tipo_operacion,
            "socio": c.socio.razon_social if c.socio else "",
            "fecha_compra": c.fecha_compra.strftime("%Y-%m-%d"),
            "tna_descuento": c.tna_descuento,
            "recurso": c.recurso,
            "iva": c.iva,
            "estado": c.estado.value if hasattr(c.estado, 'value') else c.estado
        })
    return result

@app.post("/api/v1/carteras/venta/preview", tags=["Carteras"])
def preview_venta_cartera(data: VentaCarteraRequest, db: Session = Depends(get_db)):
    try:
        from src.database.models import Credito, Cliente, Cuota
        
        # Sincronizar estados automáticamente antes de consultar la cartera disponible
        sync_system_states(db)
        
        sell_manager = PortfolioSell(db)
        
        if data.usar_cuotas_guardadas and data.cartera_id:
            df_seleccion = sell_manager.fetch_installments_from_cartera(data.cartera_id)
        else:
            df_seleccion = sell_manager.fetch_available_installments_for_sale(
                mora=data.mora,
                fecha_emision_desde=data.fecha_emision_desde,
                fecha_emision_hasta=data.fecha_emision_hasta,
                fecha_vencimiento_desde=data.fecha_vencimiento_desde,
                fecha_vencimiento_hasta=data.fecha_vencimiento_hasta,
                cartera_id=data.cartera_id
            )
        
        if df_seleccion is None or df_seleccion.empty:
            return {"creditos": [], "cuotas": [], "resumen": []}
            
        if data.creditos_excluidos:
            df_seleccion = df_seleccion[~df_seleccion['credito_id'].isin(data.creditos_excluidos)]
            if df_seleccion.empty:
                return {"creditos": [], "cuotas": [], "resumen": []}
            
        creditos_ids = df_seleccion['credito_id'].unique().tolist()
        cuotas_vendidas_ids = df_seleccion['cuota_id'].tolist()
        cuotas_por_credito = df_seleccion.groupby('credito_id').size().to_dict()
        
        fecha_v_dt = pd.to_datetime(data.fecha_venta).date() if isinstance(data.fecha_venta, str) else data.fecha_venta
        tna = float(data.tna_descuento)
        
        def calculate_va(monto, fecha_venc):
            fv = pd.to_datetime(fecha_venc).date() if isinstance(fecha_venc, str) else fecha_venc
            dias = max(0, (fv - fecha_v_dt).days)
            return float(monto) / (1 + (tna *30 / 365) * (dias/30))
        
        # 1. Fetch related Credits
        creditos_db = db.query(Credito, Cliente).join(Cliente, Credito.cliente_cuil == Cliente.cuil).filter(Credito.id.in_(creditos_ids)).all()
        
        va_por_credito = {c.id: 0.0 for c, _ in creditos_db}
        
        # 2. Fetch related Installments (all from these credits)
        cuotas_db = db.query(Cuota).filter(Cuota.credito_id.in_(creditos_ids)).order_by(Cuota.credito_id, Cuota.nro_cuota).all()
        
        cuotas_res = []
        for c in cuotas_db:
            incluida = c.id in cuotas_vendidas_ids
            
            iva_val = float(c.iva)
            if not data.iva:
                iva_val = 0.0
                
            total_c = float(c.capital) + float(c.interes) + iva_val
            
            va_cuota = 0.0
            if incluida:
                va_cuota = calculate_va(total_c, c.fecha_vencimiento)
                va_por_credito[c.credito_id] += va_cuota
                
            cuotas_res.append({
                "id": c.id,
                "credito_id": c.credito_id,
                "nro_cuota": c.nro_cuota,
                "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
                "capital": float(c.capital),
                "interes": float(c.interes),
                "iva": iva_val,
                "total_cuota": total_c,
                "valor_actual": va_cuota if incluida else 0.0,
                "incluida": incluida
            })

        creditos_res = []
        for cred, cli in creditos_db:
            creditos_res.append({
                "id": cred.id,
                "cliente": f"{cli.nombre} {cli.apellido}",
                "monto_otorgado": float(cred.capital),
                "fecha_emision": cred.fecha_emision.isoformat() if cred.fecha_emision else None,
                "total_cuotas": cred.plazo,
                "estado": cred.estado.value if hasattr(cred.estado, 'value') else str(cred.estado),
                "cuotas_a_ceder": int(cuotas_por_credito.get(cred.id, 0)),
                "valor_actual": float(va_por_credito.get(cred.id, 0.0))
            })
            
        # 3. Group summary by fecha_vencimiento for *sold* installments
        df_vendidas = df_seleccion.copy()
        
        if not data.iva:
            df_vendidas['iva'] = 0.0
            
        df_vendidas['total_cuota'] = df_vendidas['capital'] + df_vendidas['interes'] + df_vendidas['iva']
        
        def calc_va_row(row):
            return calculate_va(row['total_cuota'], row['fecha_vencimiento'])
            
        df_vendidas['valor_actual'] = df_vendidas.apply(calc_va_row, axis=1)
        
        summary_df = df_vendidas.groupby('fecha_vencimiento').agg({
            'capital': 'sum',
            'interes': 'sum',
            'iva': 'sum',
            'total_cuota': 'sum',
            'valor_actual': 'sum',
            'cuota_id': 'count'
        }).reset_index()
        
        summary_df.rename(columns={'cuota_id': 'cantidad'}, inplace=True)
        summary_df.sort_values('fecha_vencimiento', inplace=True)
        
        resumen_res = summary_df.to_dict(orient='records')
        for r in resumen_res:
            r['fecha_vencimiento'] = r['fecha_vencimiento'].isoformat() if hasattr(r['fecha_vencimiento'], 'isoformat') else str(r['fecha_vencimiento'])
            
        return {
            "creditos": creditos_res,
            "cuotas": cuotas_res,
            "resumen": resumen_res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/carteras/venta", tags=["Carteras"])
def create_venta_cartera(data: VentaCarteraRequest, db: Session = Depends(get_db)):
    try:
        # Sincronizar estados automáticamente antes de consultar la cartera disponible
        sync_system_states(db)
        
        sell_manager = PortfolioSell(db)
        
        # 1. Fetch available installments
        df_seleccion = sell_manager.fetch_available_installments_for_sale(
            mora=data.mora,
            fecha_emision_desde=data.fecha_emision_desde,
            fecha_emision_hasta=data.fecha_emision_hasta,
            fecha_vencimiento_desde=data.fecha_vencimiento_desde,
            fecha_vencimiento_hasta=data.fecha_vencimiento_hasta
        )
        
        if df_seleccion is None or df_seleccion.empty:
            raise HTTPException(status_code=400, detail="No se encontraron cuotas disponibles para vender con los criterios seleccionados.")
            
        if data.creditos_excluidos:
            df_seleccion = df_seleccion[~df_seleccion['credito_id'].isin(data.creditos_excluidos)]
            if df_seleccion.empty:
                raise HTTPException(status_code=400, detail="Todos los créditos fueron excluidos manualmente.")
            
        # 2. Execute sale
        cartera = sell_manager.execute_portfolio_sale(
            nombre_cartera=data.nombre_cartera,
            fecha_venta=data.fecha_venta,
            tna_descuento=data.tna_descuento,
            cuit_comprador=data.cuit_comprador,
            razon_social_comprador=data.razon_social_comprador,
            df_seleccion=df_seleccion,
            recurso=data.recurso,
            iva=data.iva
        )
        
        return {"status": "success", "message": f"Venta registrada exitosamente. Cartera ID: {cartera.id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/carteras/venta/{cartera_id}", tags=["Carteras"])
def update_venta_cartera(cartera_id: int, data: VentaCarteraRequest, db: Session = Depends(get_db)):
    try:
        sync_system_states(db)
        sell_manager = PortfolioSell(db)
        
        if data.usar_cuotas_guardadas:
            df_seleccion = sell_manager.fetch_installments_from_cartera(cartera_id)
        else:
            df_seleccion = sell_manager.fetch_available_installments_for_sale(
                mora=data.mora,
                fecha_emision_desde=data.fecha_emision_desde,
                fecha_emision_hasta=data.fecha_emision_hasta,
                fecha_vencimiento_desde=data.fecha_vencimiento_desde,
                fecha_vencimiento_hasta=data.fecha_vencimiento_hasta,
                cartera_id=data.cartera_id
            )
            
        if df_seleccion is None or df_seleccion.empty:
            raise HTTPException(status_code=400, detail="No se encontraron cuotas para actualizar la venta.")
            
        if data.creditos_excluidos:
            df_seleccion = df_seleccion[~df_seleccion['credito_id'].isin(data.creditos_excluidos)]
            if df_seleccion.empty:
                raise HTTPException(status_code=400, detail="Todos los créditos fueron excluidos manualmente.")
            
        cartera = sell_manager.update_portfolio_sale(
            cartera_id=cartera_id,
            nombre_cartera=data.nombre_cartera,
            fecha_venta=data.fecha_venta,
            tna_descuento=data.tna_descuento,
            cuit_comprador=data.cuit_comprador,
            razon_social_comprador=data.razon_social_comprador,
            df_seleccion=df_seleccion,
            recurso=data.recurso,
            iva=data.iva
        )
        
        return {"status": "success", "message": f"Cartera {cartera.id} actualizada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/carteras/compra", tags=["Carteras"])
async def create_compra_cartera(
    nombre_cartera: str = Form(...),
    fecha_compra: date = Form(...),
    tna_descuento: float = Form(...),
    cuit_vendedor: str = Form(...),
    razon_social_vendedor: str = Form(...),
    personas_csv: UploadFile = File(...),
    prestamos_csv: UploadFile = File(...),
    cuotas_csv: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    import tempfile
    import os
    
    # Save uploaded files temporarily
    with tempfile.TemporaryDirectory() as temp_dir:
        p_personas = os.path.join(temp_dir, "personas.csv")
        p_prestamos = os.path.join(temp_dir, "prestamos.csv")
        p_cuotas = os.path.join(temp_dir, "cuotas.csv")
        
        with open(p_personas, "wb") as f: f.write(await personas_csv.read())
        with open(p_prestamos, "wb") as f: f.write(await prestamos_csv.read())
        with open(p_cuotas, "wb") as f: f.write(await cuotas_csv.read())
        
        try:
            from src.portfolio.purchase import PortfolioPurchase
            importer = PortfolioPurchase()
            
            importer.create_portfolio(
                nombre_cartera=nombre_cartera,
                fecha_compra=fecha_compra,
                tna_descuento=tna_descuento,
                cuit_vendedor=cuit_vendedor,
                razon_social_vendedor=razon_social_vendedor
            )
            
            importer.read_csv(
                personas_path=p_personas,
                prestamos_path=p_prestamos,
                cuotas_path=p_cuotas
            )
            
            importer.validation()
            importer.check_warnings()
            importer.process_full_portfolio()
            importer.save_portfolio()
            
            return {"status": "success", "message": "Compra de cartera importada exitosamente."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/v1/carteras/{cartera_id}", tags=["Carteras"])
def update_cartera(cartera_id: int, data: UpdateCarteraRequest, db: Session = Depends(get_db)):
    from src.database.models import Cartera, EstadoCartera, EstadoCuotaCedida, TipoOperacionCartera, Cuota
    
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
    if cartera.estado != EstadoCartera.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden modificar carteras en estado PENDIENTE.")
        
    try:
        if data.fecha_compra is not None:
            cartera.fecha_compra = data.fecha_compra
        if data.tna_descuento is not None:
            cartera.tna_descuento = data.tna_descuento
        if data.recurso is not None:
            cartera.recurso = data.recurso
        if data.iva is not None:
            cartera.iva = data.iva
            
        if data.estado is not None:
            nuevo_estado_str = data.estado.upper()
            if nuevo_estado_str in ["VENDIDA", "COMPRADA"]:
                if nuevo_estado_str == "VENDIDA" and cartera.tipo_operacion != TipoOperacionCartera.VENTA:
                    raise ValueError("El estado VENDIDA solo aplica a carteras de VENTA.")
                if nuevo_estado_str == "COMPRADA" and cartera.tipo_operacion != TipoOperacionCartera.COMPRA:
                    raise ValueError("El estado COMPRADA solo aplica a carteras de COMPRA.")
                
                cartera.estado = EstadoCartera[nuevo_estado_str]
                
                # Actualizar masivamente las cuotas a su estado final
                cuotas_ids = [op.cuota_id for op in cartera.operaciones]
                if cuotas_ids:
                    db.query(Cuota).filter(Cuota.id.in_(cuotas_ids)).update(
                        {"estado_cesion": EstadoCuotaCedida.PENDIENTE},
                        synchronize_session=False
                    )
            elif nuevo_estado_str == "PENDIENTE":
                pass # Ya está pendiente
            else:
                raise ValueError(f"Estado {nuevo_estado_str} no es válido.")

        db.commit()
        return {"status": "success", "message": "Cartera actualizada correctamente."}
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/carteras/{cartera_id}", tags=["Carteras"])
def delete_cartera(cartera_id: int, db: Session = Depends(get_db)):
    from src.database.models import Cartera, OperacionCartera, Cuota, EstadoCuotaCedida, EstadoCartera, TipoOperacionCartera, Credito
    
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
    if cartera.estado != EstadoCartera.PENDIENTE:
        raise HTTPException(status_code=400, detail="No se puede eliminar una cartera que ya está CONFIRMADA (VENDIDA o COMPRADA).")
    
    try:
        if cartera.tipo_operacion == TipoOperacionCartera.COMPRA:
            # En una COMPRA, los créditos se crearon específicamente para esta cartera.
            # Al eliminarlos, SQLAlchemy (o la BD) debería aplicar cascade a las Cuotas y a OperacionCartera.
            # Primero eliminamos las Operaciones relacionadas para evitar problemas si faltan cascades
            db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).delete(synchronize_session=False)
            
            # Buscamos los creditos asociados y los borramos uno por uno para asegurar los cascades a nivel ORM si es necesario
            creditos_asociados = db.query(Credito).filter(Credito.cartera_id == cartera_id).all()
            for cred in creditos_asociados:
                db.delete(cred)
            
        else:
            # En una VENTA, la cartera solo agrupa cuotas existentes.
            # Get all related OperacionCartera records
            operaciones = db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).all()
            cuota_ids = [op.cuota_id for op in operaciones]
    
            # Revert estado_cesion for the affected cuotas
            if cuota_ids:
                db.query(Cuota).filter(Cuota.id.in_(cuota_ids)).update(
                    {"estado_cesion": EstadoCuotaCedida.NO_VENDIDA},
                    synchronize_session=False
                )
    
            # Delete related OperacionCartera mapping records
            db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).delete(synchronize_session=False)

        # Delete the Cartera itself
        db.delete(cartera)
        db.commit()
        return {"status": "success", "message": f"Cartera {cartera_id} eliminada correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se puede eliminar la cartera (puede estar referenciada). Error: {str(e)}")

# -------------------------------------------------------------------
# Frontend
# -------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
