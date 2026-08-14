from datetime import datetime
from typing import Any, Dict, List, Optional
import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.reports.balances import saldos, cobranzas_recibidas

router = APIRouter(prefix="/api/v1/reports", tags=["Reportes"])

@router.get("/balances")
def get_saldos(
    fecha: Optional[datetime] = Query(None, description="Fecha de corte para el cálculo. Por defecto es hoy."),
    con_saldo: bool = Query(True, description="Filtra solo las operaciones que aún mantienen saldo deudor."),
    propias: Optional[bool] = Query(None, description="Verdadero para cartera propia, Falso para terceros, Nulo para ambas."),
    agrupar: bool = Query(False, description="Activa el pipeline de agrupación dinámico."),
    agrupadores: Optional[str] = Query(None, description="Lista ordenada de agrupadores separados por coma."),
) -> List[Dict[str, Any]]:
    """
    Expone la generación del reporte de saldos. Devuelve los registros crudos o 
    agrupados desde el core engine, mapeados como una estructura JSON-friendly.
    """
    try:
        lista_agrupadores = agrupadores.split(',') if agrupadores else None

        df = saldos(
            fecha=fecha,
            con_saldo=con_saldo,
            propias=propias,
            agrupar=agrupar,
            agrupadores=lista_agrupadores,
        )

        df = df.reset_index()
        df = df.replace({np.nan: None})

        for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")

        return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la generación del reporte: {str(e)}")

@router.get("/balances/evolution")
def get_saldos_evolution(
    meses: int = Query(12, description="Cantidad de meses hacia atrás"),
    propias: Optional[bool] = Query(None, description="Verdadero para cartera propia, Falso para terceros, Nulo para ambas."),
    fecha: Optional[datetime] = Query(None, description="Fecha base para calcular los meses hacia atrás")
) -> List[Dict[str, Any]]:
    try:
        base_date = fecha if fecha else datetime.today()
        results = []
        for i in range(meses - 1, -1, -1):
            fecha_corte = base_date - pd.DateOffset(months=i)
            df = saldos(fecha=fecha_corte, con_saldo=True, propias=propias, agrupar=True, agrupadores=["dueno", "originador"])
            
            detalles = []
            if not df.empty:
                df = df.reset_index()
                for _, row in df.iterrows():
                    detalles.append({
                        "Dueño": str(row.get("Dueño", "Desconocido") or "Desconocido"),
                        "Originador": str(row.get("Originador", "N/A") or "N/A"),
                        "capital": float(row.get("Capital", 0)),
                        "interes": float(row.get("Interés", 0)),
                        "iva": float(row.get("IVA", 0)),
                        "total": float(row.get("Total", 0)),
                    })
                
            results.append({
                "periodo": fecha_corte.strftime("%Y-%m"),
                "fecha": fecha_corte.strftime("%Y-%m-%d"),
                "detalles": detalles
            })
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evolución: {str(e)}")

@router.get("/balances/excel")
def export_saldos_excel(
    fecha: Optional[datetime] = Query(None, description="Fecha de corte para el cálculo. Por defecto es hoy."),
    con_saldo: bool = Query(True, description="Filtra solo las operaciones que aún mantienen saldo deudor."),
    propias: Optional[bool] = Query(None, description="Verdadero para cartera propia, Falso para terceros, Nulo para ambas."),
    agrupar: bool = Query(False, description="Activa el pipeline de agrupación dinámico."),
    agrupadores: Optional[str] = Query(None, description="Lista ordenada de agrupadores separados por coma."),
):
    try:
        lista_agrupadores = agrupadores.split(',') if agrupadores else None
        
        df = saldos(
            fecha=fecha, con_saldo=con_saldo, propias=propias, agrupar=agrupar,
            agrupadores=lista_agrupadores
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

@router.get("/cobranzas/evolution")
def get_cobranzas_evolution(
    meses: int = Query(12, description="Cantidad de meses hacia atrás"),
    fecha: Optional[datetime] = Query(None, description="Fecha de corte")
) -> List[Dict[str, Any]]:
    try:
        from src.reports.balances import cuotas_teoricas
        df = cobranzas_recibidas(meses=meses, fecha=fecha)
        df_teo = cuotas_teoricas(meses=meses, fecha=fecha)
        
        if df.empty and df_teo.empty:
            return []

        df = df.replace({np.nan: None})
        if not df_teo.empty:
            df_teo = df_teo.replace({np.nan: None})

        # To return the data, we want to group it by "periodo"
        # and nest the details just like balances/evolution does
        results = []
        
        # Get all unique periods from both dfs
        periodos_cobr = set(df["periodo"].unique()) if not df.empty else set()
        periodos_teo = set(df_teo["periodo"].unique()) if not df_teo.empty else set()
        all_periodos = sorted(list(periodos_cobr | periodos_teo))

        for periodo in all_periodos:
            detalles = []
            teoricos = []
            
            if not df.empty and periodo in periodos_cobr:
                group = df[df["periodo"] == periodo]
                for _, row in group.iterrows():
                    detalles.append({
                        "Dueño": str(row.get("Dueño") or "Desconocido"),
                        "Originador": str(row.get("Originador") or "N/A"),
                        "tipo_cobranza": str(row.get("tipo_cobranza") or "COMUN"),
                        "capital": float(row.get("capital", 0)),
                        "interes": float(row.get("interes", 0)),
                        "iva": float(row.get("iva", 0)),
                        "total": float(row.get("total", 0)),
                        "recupero_mora": float(row.get("recupero_mora", 0)),
                    })
                    
            if not df_teo.empty and periodo in periodos_teo:
                group_teo = df_teo[df_teo["periodo"] == periodo]
                for _, row in group_teo.iterrows():
                    teoricos.append({
                        "Dueño": str(row.get("Dueño") or "Desconocido"),
                        "Originador": str(row.get("Originador") or "N/A"),
                        "capital": float(row.get("capital", 0)),
                        "interes": float(row.get("interes", 0)),
                        "iva": float(row.get("iva", 0)),
                        "total": float(row.get("total", 0)),
                        "total_cobr": float(row.get("total_cobr", 0)),
                    })
            
            results.append({
                "periodo": periodo,
                "detalles": detalles,
                "teoricos": teoricos
            })
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evolución de cobranzas: {str(e)}")

@router.get("/esp")
def get_esp(
    fecha: Optional[datetime] = Query(None, description="Fecha de corte para el cálculo. Por defecto es hoy."),
    periodos: int = Query(2, description="Cantidad de periodos a mostrar"),
    salto: int = Query(1, description="Salto en meses entre periodos"),
    tna_descuento: float = Query(0.0, description="Tasa Nominal Anual por defecto si no hay carteras previas")
) -> Dict[str, Any]:
    """
    Genera el reporte de Estado de Situación Patrimonial (ESP).
    """
    try:
        from src.reports.finance.esp import reporte
        if fecha is None:
            fecha = datetime.today()
        
        df = reporte(fecha_corte=fecha, n_periodos=periodos, salto_meses=salto, tna_descuento=tna_descuento)
        
        # Reset MultiIndex to convert to records
        df = df.reset_index()
        df = df.replace({np.nan: None})
        
        return {
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte ESP: {str(e)}")
