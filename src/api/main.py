"""
Module: main.py
Description: FastAPI entry point located in src/api.
Author: Juan Martín Carini
Date: 2026-05-11
"""

from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.logic.amortization import AmortizationEngine
from src.reports import saldos

app = FastAPI(title="Credit Manager API")


@app.get("/")
def read_root():
    return {"status": "online", "user": "Gandalf"}


@app.get("/simular-cuotas")
def simular(capital: float, tna: float, cuotas: int, dia_vto: int = 28):
    """
    Endpoint para probar la lógica de amortización rápidamente.
    """
    try:
        # Usamos el motor de lógica que ya validamos en el notebook
        resultado = AmortizationEngine.generate_french_schedule(
            credito_id=0,
            capital=capital,
            tna_c_iva=tna,
            plazo=cuotas,
            fecha_emision=date.today(),
            dia_vencimiento=dia_vto,
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports/balances")
def get_portfolio_balances(fecha: str = None, agrupar: bool = False):
    """
    Exposes the portfolio balance report as a JSON object.
    """
    try:
        # Convert string date from request to datetime object if provided
        cut_off = pd.to_datetime(fecha) if fecha else None

        # Get raw numeric data
        df = saldos(fecha=cut_off, agrupar=agrupar, socios=agrupar)

        # Convert to list of dicts (JSON ready)
        # We replace NaN with None to ensure valid JSON 'null' values
        return (
            df.reset_index()
            .replace({pd.NA: None, float("nan"): None})
            .to_dict(orient="records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
