from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response

from src.reports.bcra_logic import generate_bcra_files, generar_reporte_personalizado_excel

router = APIRouter(prefix="/api/v1/bcra", tags=["BCRA Reportes"])


@router.get("/export")
def export_bcra_report(
    fecha_corte: date = Query(..., description="Fecha de corte para el reporte."),
    vto_hasta: Optional[date] = Query(None, description="Fecha de vencimiento hasta."),
    origen: Optional[str] = Query(None, description="Origen del crédito (Comprados, Propios)."),
    socio_originador: Optional[str] = Query(None, description="Filtro por Socio Originador."),
    nro_orden: Optional[str] = Query(None, description="Filtro por ID Credito (interno)."),
    sit_mora: Optional[str] = Query(None, description="Filtro por situación BCRA (ej. '01', '02')."),
    comprado: Optional[str] = Query(None, description="'Ambas', 'Propias' o 'Terceros'."),
    min_monto_mora: Optional[float] = Query(None, description="Límite mínimo de monto de mora."),
    tipo_reporte: Optional[str] = Query("NORMAL", description="NORMAL o RECTIFICATORIO"),
    cliente: Optional[str] = Query(None, description="ID, CUIL, o DNI del cliente para rectificatorio."),
):
    try:
        zip_bytes = generate_bcra_files(
            fecha_corte=fecha_corte,
            vto_hasta=vto_hasta,
            origen=origen,
            socio_originador=socio_originador,
            nro_orden=nro_orden,
            sit_mora=sit_mora,
            comprado=comprado,
            min_monto_mora=min_monto_mora,
            tipo_reporte=tipo_reporte,
            cliente=cliente,
        )
        
        headers = {
            'Content-Disposition': 'attachment; filename="reporte_bcra_pnfc.zip"'
        }
        return Response(content=zip_bytes, media_type="application/zip", headers=headers)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte BCRA: {str(e)}")


@router.get("/excel")
def export_normal_excel(
    fecha_corte: date = Query(..., description="Fecha de corte para el reporte."),
    vto_hasta: Optional[date] = Query(None, description="Fecha de vencimiento hasta."),
    origen: Optional[str] = Query(None, description="Origen del crédito (Comprados, Propios)."),
    socio_originador: Optional[str] = Query(None, description="Filtro por Socio Originador."),
    nro_orden: Optional[str] = Query(None, description="Filtro por ID Credito (interno)."),
    sit_mora: Optional[str] = Query(None, description="Filtro por situación BCRA (ej. '01', '02')."),
    comprado: Optional[str] = Query(None, description="'Ambas', 'Propias' o 'Terceros'."),
    min_monto_mora: Optional[float] = Query(None, description="Límite mínimo de monto de mora."),
    tipo_reporte: Optional[str] = Query("NORMAL", description="NORMAL o RECTIFICATORIO"),
    cliente: Optional[str] = Query(None, description="ID, CUIL, o DNI del cliente para rectificatorio."),
):
    try:
        excel_bytes_io = generar_reporte_personalizado_excel(
            fecha_corte=fecha_corte,
            vto_hasta=vto_hasta,
            origen=origen,
            socio_originador=socio_originador,
            nro_orden=nro_orden,
            sit_mora=sit_mora,
            comprado=comprado,
            min_monto_mora=min_monto_mora,
            tipo_reporte=tipo_reporte,
            cliente=cliente,
        )
        
        headers = {
            'Content-Disposition': 'attachment; filename="reporte_normal_filtrado.xlsx"'
        }
        return StreamingResponse(
            excel_bytes_io, 
            headers=headers, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel normal: {str(e)}")
