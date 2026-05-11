"""
Module: main.py
Description: FastAPI entry point located in src/api.
Author: Juan Martín Carini
Date: 2026-05-11
"""

from datetime import date

from fastapi import FastAPI, HTTPException

from src.logic.amortization import AmortizationEngine

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
