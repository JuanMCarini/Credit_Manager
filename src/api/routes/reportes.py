from datetime import datetime
from typing import Any, Dict, List, Optional
import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.reports.balances import saldos

router = APIRouter(prefix="/api/v1/reports", tags=["Reportes"])

@router.get("/balances")
def get_saldos(
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

        df = df.reset_index()
        df = df.replace({np.nan: None})

        for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")

        return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la generación del reporte: {str(e)}")

@router.get("/balances/excel")
def export_saldos_excel(
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
