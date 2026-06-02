"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from src.logic.amortization import AmortizationEngine
from src.reports.balances import saldos

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
app = FastAPI(
    title="Credit Manager Core Engine API",
    description="API RESTful para interactuar con el motor financiero de gestión de cartera de créditos.",
    version="1.0.0",
)

# Permitir orígenes para desarrollo (Vite típicamente usa localhost:5173 o 127.0.0.1:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción debe limitarse al dominio del frontend
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

# -------------------------------------------------------------------
# Frontend
# -------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
