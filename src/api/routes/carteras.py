import os
import tempfile
import zipfile
import pandas as pd
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session, joinedload

from src.database import get_db
from src.database.models import Cartera, EstadoCartera, EstadoCuotaCedida, TipoOperacionCartera, Cuota, OperacionCartera, Credito, Cliente
from src.api.schemas.carteras import VentaCarteraRequest, UpdateCarteraRequest
from src.portfolio.sell import PortfolioSell
from src.portfolio.purchase import PortfolioPurchase
from src.api.routes.system import sync_system_states
from src.api.routes.creditos import _merge_uploaded_docs_for_credito

router = APIRouter(prefix="/api/v1/carteras", tags=["Carteras"])

@router.get("")
def get_carteras(db: Session = Depends(get_db)):
    from src.database.models import SocioComercial
    carteras = db.query(Cartera).options(joinedload(Cartera.socio)).all()
    
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

@router.post("/venta/preview")
def preview_venta_cartera(data: VentaCarteraRequest, db: Session = Depends(get_db)):
    try:
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
                cuotas_completas=data.cuotas_completas,
                socio_originador_id=data.socio_originador_id,
                cartera_id=data.cartera_id
            )
        
        if df_seleccion is None or df_seleccion.empty:
            return {"creditos": [], "cuotas": [], "resumen": []}
            
        creditos_ids_all = df_seleccion['credito_id'].unique().tolist()
        
        df_vendidas = df_seleccion.copy()
        if data.creditos_excluidos:
            df_vendidas = df_vendidas[~df_vendidas['credito_id'].isin(data.creditos_excluidos)]
            
        cuotas_vendidas_ids = df_vendidas['cuota_id'].tolist() if not df_vendidas.empty else []
        cuotas_por_credito = df_vendidas.groupby('credito_id').size().to_dict() if not df_vendidas.empty else {}
        
        fecha_v_dt = pd.to_datetime(data.fecha_venta).date() if isinstance(data.fecha_venta, str) else data.fecha_venta
        tna = float(data.tna_descuento)
        
        def calculate_va(monto, fecha_venc):
            fv = pd.to_datetime(fecha_venc).date() if isinstance(fecha_venc, str) else fecha_venc
            dias = max(0, (fv - fecha_v_dt).days)
            return round(float(monto) / ((1 + (tna *30 / 365)) ** (dias/30)), 2)

        creditos_db = db.query(Credito, Cliente).join(Cliente, Credito.cliente_cuil == Cliente.cuil).filter(Credito.id.in_(creditos_ids_all)).all()
        va_por_credito = {c.id: 0.0 for c, _ in creditos_db}
        
        cuotas_db = db.query(Cuota).filter(Cuota.credito_id.in_(creditos_ids_all)).order_by(Cuota.credito_id, Cuota.nro_cuota).all()
        
        cuotas_res = []
        for c in cuotas_db:
            incluida = c.id in cuotas_vendidas_ids
            iva_val = float(c.iva)
            if not data.iva:
                iva_val = 0.0
                
            total_c = round(round(float(c.capital), 2) + round(float(c.interes), 2), 2)
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
            
        if not data.iva:
            df_vendidas['iva'] = 0.0
            
        if df_vendidas.empty:
            resumen_res = []
        else:
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

@router.post("/venta")
def create_venta_cartera(data: VentaCarteraRequest, db: Session = Depends(get_db)):
    try:
        sync_system_states(db)
        sell_manager = PortfolioSell(db)
        
        df_seleccion = sell_manager.fetch_available_installments_for_sale(
            mora=data.mora,
            fecha_emision_desde=data.fecha_emision_desde,
            fecha_emision_hasta=data.fecha_emision_hasta,
            fecha_vencimiento_desde=data.fecha_vencimiento_desde,
            fecha_vencimiento_hasta=data.fecha_vencimiento_hasta,
            cuotas_completas=data.cuotas_completas,
            socio_originador_id=data.socio_originador_id
        )
        
        if df_seleccion is None or df_seleccion.empty:
            raise HTTPException(status_code=400, detail="No se encontraron cuotas disponibles para vender con los criterios seleccionados.")
            
        if data.creditos_excluidos:
            df_seleccion = df_seleccion[~df_seleccion['credito_id'].isin(data.creditos_excluidos)]
            if df_seleccion.empty:
                raise HTTPException(status_code=400, detail="Todos los créditos fueron excluidos manualmente.")
            
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

@router.put("/venta/{cartera_id}")
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
                cuotas_completas=data.cuotas_completas,
                socio_originador_id=data.socio_originador_id,
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

@router.post("/compra/preview")
def preview_compra_cartera(
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
    with tempfile.TemporaryDirectory() as temp_dir:
        p_personas = os.path.join(temp_dir, "personas.csv")
        p_prestamos = os.path.join(temp_dir, "prestamos.csv")
        p_cuotas = os.path.join(temp_dir, "cuotas.csv")
        
        with open(p_personas, "wb") as f: f.write(personas_csv.file.read())
        with open(p_prestamos, "wb") as f: f.write(prestamos_csv.file.read())
        with open(p_cuotas, "wb") as f: f.write(cuotas_csv.file.read())
        
        try:
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
            
            df_personas = importer.df_personas
            df_prestamos = importer.df_prestamos
            df_cuotas = importer.df_cuotas
            
            if not df_personas.empty and not df_prestamos.empty:
                cols_to_merge = [c for c in ['ID Operación', 'CUIL', 'Apellido', 'Nombre', 'Remuneración'] if c in df_personas.columns]
                df_merged = pd.merge(df_prestamos, df_personas[cols_to_merge], on='ID Operación', how='left')
                df_merged['Cliente'] = df_merged['Apellido'].fillna('') + ' ' + df_merged['Nombre'].fillna('')
            else:
                df_merged = df_prestamos.copy()
                df_merged['Cliente'] = "Desconocido"
                
            fecha_v_dt = pd.to_datetime(fecha_compra).date() if isinstance(fecha_compra, str) else fecha_compra
            tna = float(tna_descuento)
            
            def safe_float(val, default=0.0):
                try:
                    v = float(val)
                    import math
                    return default if math.isnan(v) else v
                except (TypeError, ValueError):
                    return default

            df_cuotas['Valor Actual'] = pd.to_numeric(df_cuotas['Valor Actual'], errors='coerce').fillna(0)
            df_cuotas_compradas = df_cuotas[df_cuotas['Valor Actual'] > 0].copy()
            
            plazo_series = df_cuotas.groupby("ID Operación").size()
            compradas_series = df_cuotas[df_cuotas["Valor Actual"] > 0].groupby("ID Operación").size()
            val_act_series = df_cuotas[df_cuotas["Valor Actual"] > 0].groupby("ID Operación")["Valor Actual"].sum()
            val_act_csv_series = df_cuotas[df_cuotas["Valor Actual"] > 0].groupby("ID Operación")["Valor Actual CSV"].sum()
            
            creditos_res = []
            for _, row in df_merged.iterrows():
                id_op = row.get("ID Operación", "")
                cap_vend = safe_float(row.get("Capital Vendido", row.get("Capital", 0)))
                int_vend = safe_float(row.get("Interés Vendido", row.get("Interés", 0)))
                iva_vend = safe_float(row.get("IVA Vendido", row.get("IVA", 0)))
                val_act = float(val_act_series.get(id_op, 0.0))
                val_act_csv = float(val_act_csv_series.get(id_op, 0.0))
                
                plazo = int(plazo_series.get(id_op, 0))
                cuotas_compradas = int(compradas_series.get(id_op, 0))
                
                remuneracion = safe_float(row.get("Remuneración", 0))
                valor_cuota = safe_float(row.get("Importe Cuota", 0))
                relacion_cuota_sueldo = 0
                if remuneracion > 0:
                    relacion_cuota_sueldo = round((valor_cuota / remuneracion) * 100, 0)
                
                f_emision = row.get("Fecha Emisión", row.get("Fecha Emision", row.get("fecha_emision", None)))
                f_emision_str = None
                if f_emision is not None and not pd.isna(f_emision):
                    if hasattr(f_emision, 'strftime'):
                        f_emision_str = f_emision.strftime("%Y-%m-%d")
                    else:
                        f_emision_str = str(f_emision).split("T")[0].split(" ")[0]

                creditos_res.append({
                    "id_externo": str(id_op),
                    "cliente_nombre": str(row.get("Cliente", "")).strip() or str(row.get("CUIL", "")),
                    "capital_vendido": cap_vend,
                    "interes_vendido": int_vend,
                    "iva_vendido": iva_vend,
                    "valor_actual": val_act,
                    "valor_actual_csv": val_act_csv,
                    "plazo": plazo,
                    "cuotas_compradas": cuotas_compradas,
                    "relacion_cuota_sueldo": relacion_cuota_sueldo,
                    "fecha_emision": f_emision_str
                })
                
            cuotas_res = []
            for _, row in df_cuotas.iterrows():
                cap = safe_float(row.get("Capital", 0))
                interes = safe_float(row.get("Interés", 0))
                iva = safe_float(row.get("IVA", 0))
                total = cap + interes + iva
                val_act = safe_float(row.get("Valor Actual", 0))
                val_act_csv = safe_float(row.get("Valor Actual CSV", 0))
                
                cuotas_res.append({
                    "credito_id_externo": str(row.get("ID Operación", "")),
                    "nro_cuota": str(row.get("ID Cuota", "")),
                    "fecha_vencimiento": str(row.get("Fecha Vto.", "")),
                    "fecha_vencimiento_pago": str(row.get("Fecha Vto. Pago", "")),
                    "capital": cap,
                    "interes": interes,
                    "iva": iva,
                    "total": total,
                    "valor_actual": val_act,
                    "valor_actual_csv": val_act_csv,
                    "comprada": val_act > 0
                })
                
            df_cuotas_compradas['Fecha Vto. parsed'] = pd.to_datetime(df_cuotas_compradas['Fecha Vto.'], dayfirst=True, errors='coerce')
            df_cuotas_compradas['Fecha Vto. parsed'] = df_cuotas_compradas['Fecha Vto. parsed'].fillna(pd.to_datetime(df_cuotas_compradas['Fecha Vto.'], errors='coerce'))
            df_cuotas_compradas['Mes_Año'] = df_cuotas_compradas['Fecha Vto. parsed'].dt.strftime('%Y-%m')
            
            df_cuotas_compradas['Fecha Pago parsed'] = pd.to_datetime(df_cuotas_compradas['Fecha Vto. Pago'], dayfirst=False, errors='coerce')
            df_cuotas_compradas['Fecha Pago parsed'] = df_cuotas_compradas['Fecha Pago parsed'].fillna(pd.to_datetime(df_cuotas_compradas['Fecha Vto. Pago'], errors='coerce'))
            df_cuotas_compradas['Mes_Año_Pago'] = df_cuotas_compradas['Fecha Pago parsed'].dt.strftime('%Y-%m')
            
            resumen_dict = {}
            for _, row in df_cuotas_compradas.iterrows():
                mes_anio = row.get('Mes_Año', 'Desconocido')
                if pd.isna(mes_anio): mes_anio = 'Desconocido'
                
                mes_pago = row.get('Mes_Año_Pago', 'Desconocido')
                if pd.isna(mes_pago): mes_pago = mes_anio
                
                cap = safe_float(row.get("Capital", 0))
                interes = safe_float(row.get("Interés", 0))
                iva = safe_float(row.get("IVA", 0))
                total = cap + interes + iva
                val_act = safe_float(row.get("Valor Actual", 0))
                val_act_csv = safe_float(row.get("Valor Actual CSV", 0))
                
                if mes_anio not in resumen_dict:
                    resumen_dict[mes_anio] = {
                        "mes": mes_anio, 
                        "mes_pago": mes_pago,
                        "cantidad_cuotas": 0, 
                        "capital_total": 0.0,
                        "interes_total": 0.0,
                        "iva_total": 0.0,
                        "monto_total": 0.0, 
                        "valor_actual": 0.0,
                        "valor_actual_csv": 0.0
                    }
                    
                resumen_dict[mes_anio]["cantidad_cuotas"] += 1
                resumen_dict[mes_anio]["capital_total"] += cap
                resumen_dict[mes_anio]["interes_total"] += interes
                resumen_dict[mes_anio]["iva_total"] += iva
                resumen_dict[mes_anio]["monto_total"] += total
                resumen_dict[mes_anio]["valor_actual"] += val_act
                resumen_dict[mes_anio]["valor_actual_csv"] += val_act_csv
                
            resumen_res = list(resumen_dict.values())
            resumen_res.sort(key=lambda x: x["mes"])
            
            for r in resumen_res:
                r["capital_total"] = round(r["capital_total"], 2)
                r["interes_total"] = round(r["interes_total"], 2)
                r["iva_total"] = round(r["iva_total"], 2)
                r["monto_total"] = round(r["monto_total"], 2)
                r["valor_actual"] = round(r["valor_actual"], 2)
                r["valor_actual_csv"] = round(r["valor_actual_csv"], 2)
            
            resumen_res = [r for r in resumen_res if r["valor_actual"] > 0]
                
            return {
                "status": "success",
                "creditos": creditos_res,
                "cuotas": cuotas_res,
                "resumen": resumen_res
            }
            
        except Exception as e:
            error_msg = str(e)
            if "REPORT_ERROR|" in error_msg:
                parts = error_msg.split("|", 2)
                if len(parts) == 3:
                    file_name = parts[1]
                    user_msg = parts[2]
                    return JSONResponse(status_code=400, content={
                        "detail": user_msg,
                        "report_file": file_name
                    })
            raise HTTPException(status_code=400, detail=error_msg)

@router.post("/compra")
def create_compra_cartera(
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
    with tempfile.TemporaryDirectory() as temp_dir:
        p_personas = os.path.join(temp_dir, "personas.csv")
        p_prestamos = os.path.join(temp_dir, "prestamos.csv")
        p_cuotas = os.path.join(temp_dir, "cuotas.csv")
        
        with open(p_personas, "wb") as f: f.write(personas_csv.file.read())
        with open(p_prestamos, "wb") as f: f.write(prestamos_csv.file.read())
        with open(p_cuotas, "wb") as f: f.write(cuotas_csv.file.read())
        
        try:
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
            importer.save_portfolio()
            
            return {"status": "success", "message": "Compra de cartera importada exitosamente."}
        except Exception as e:
            error_msg = str(e)
            if "REPORT_ERROR|" in error_msg:
                parts = error_msg.split("|", 2)
                if len(parts) == 3:
                    file_name = parts[1]
                    user_msg = parts[2]
                    return JSONResponse(status_code=400, content={
                        "detail": user_msg,
                        "report_file": file_name
                    })
            raise HTTPException(status_code=400, detail=error_msg)

@router.get("/compra/reportes/{filename}")
def download_import_report(filename: str):
    if "REPORTE" not in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    import tempfile
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
        
    return FileResponse(file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@router.get("/compra/{cartera_id}/preview")
def get_compra_preview(cartera_id: int, db: Session = Depends(get_db)):
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera or cartera.tipo_operacion != TipoOperacionCartera.COMPRA:
        raise HTTPException(status_code=404, detail="Cartera de compra no encontrada")
        
    creditos = db.query(Credito, Cliente).join(Cliente, Credito.cliente_cuil == Cliente.cuil).filter(Credito.cartera_id == cartera_id).all()
    if not creditos:
        return {"creditos": [], "cuotas": [], "resumen": []}
        
    creditos_ids = [c.id for c, _ in creditos]
    cuotas = db.query(Cuota).filter(Cuota.credito_id.in_(creditos_ids)).all()
    
    operaciones = db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).all()
    cuota_comprada_map = {op.cuota_id: op.cuota_comercializada for op in operaciones}
    
    fecha_compra_dt = pd.to_datetime(cartera.fecha_compra).date()
    tna = float(cartera.tna_descuento)
    
    def calculate_va(monto, fecha_venc):
        fv = pd.to_datetime(fecha_venc).date() if isinstance(fecha_venc, str) else fecha_venc
        if fv is None: return 0.0
        dias = max(0, (fv - fecha_compra_dt).days)
        return round(float(monto) / ((1 + (tna * 30 / 365)) ** (dias/30)), 2)

    cuotas_res = []
    va_por_credito = {c.id: 0.0 for c, _ in creditos}
    cuotas_compradas_por_cred = {c.id: 0 for c, _ in creditos}
    
    df_cuotas_data = []
    cred_ext_map = {c.id: c.id_externo for c, _ in creditos}
    
    for c in cuotas:
        comprada = cuota_comprada_map.get(c.id, False)
        total = round(float(c.capital) + float(c.interes) + float(c.iva), 2)
        va = calculate_va(total, c.fecha_vencimiento) if comprada else 0.0
        
        if comprada:
            va_por_credito[c.credito_id] += va
            cuotas_compradas_por_cred[c.credito_id] += 1
            
        cuotas_res.append({
            "credito_id_externo": str(cred_ext_map.get(c.credito_id, c.credito_id)),
            "nro_cuota": str(c.nro_cuota),
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else "",
            "fecha_vencimiento_pago": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else "",
            "capital": float(c.capital),
            "interes": float(c.interes),
            "iva": float(c.iva),
            "total": total,
            "valor_actual": va,
            "valor_actual_csv": va,
            "comprada": comprada
        })
        
        if comprada:
            df_cuotas_data.append({
                "fecha_vencimiento": c.fecha_vencimiento,
                "capital": float(c.capital),
                "interes": float(c.interes),
                "iva": float(c.iva),
                "total": total,
                "valor_actual": va
            })
            
    creditos_res = []
    for cred, cli in creditos:
        cap_v = sum(float(c.capital) for c in cuotas if c.credito_id == cred.id and cuota_comprada_map.get(c.id, False))
        int_v = sum(float(c.interes) for c in cuotas if c.credito_id == cred.id and cuota_comprada_map.get(c.id, False))
        iva_v = sum(float(c.iva) for c in cuotas if c.credito_id == cred.id and cuota_comprada_map.get(c.id, False))
        
        creditos_res.append({
            "id_externo": str(cred.id_externo or cred.id),
            "cliente_nombre": f"{cli.apellido} {cli.nombre}".strip(),
            "capital_vendido": cap_v,
            "interes_vendido": int_v,
            "iva_vendido": iva_v,
            "valor_actual": round(va_por_credito[cred.id], 2),
            "valor_actual_csv": round(va_por_credito[cred.id], 2),
            "plazo": cred.plazo,
            "cuotas_compradas": cuotas_compradas_por_cred[cred.id],
            "relacion_cuota_sueldo": 0.0,
            "fecha_emision": cred.fecha_emision.isoformat() if cred.fecha_emision else None
        })
        
    resumen_res = []
    if df_cuotas_data:
        df = pd.DataFrame(df_cuotas_data)
        df['fecha_vencimiento_pd'] = pd.to_datetime(df['fecha_vencimiento'])
        df['mes'] = df['fecha_vencimiento_pd'].dt.strftime('%Y-%m')
        
        summary = df.groupby('mes').agg({
            'capital': 'sum',
            'interes': 'sum',
            'iva': 'sum',
            'total': 'sum',
            'valor_actual': 'sum',
            'fecha_vencimiento': 'count'
        }).reset_index()
        
        for _, row in summary.iterrows():
            resumen_res.append({
                "mes": row['mes'],
                "mes_pago": row['mes'],
                "cantidad_cuotas": int(row['fecha_vencimiento']),
                "capital_total": round(float(row['capital']), 2),
                "interes_total": round(float(row['interes']), 2),
                "iva_total": round(float(row['iva']), 2),
                "monto_total": round(float(row['total']), 2),
                "valor_actual": round(float(row['valor_actual']), 2),
                "valor_actual_csv": round(float(row['valor_actual']), 2)
            })
            
    return {
        "status": "success",
        "creditos": creditos_res,
        "cuotas": cuotas_res,
        "resumen": resumen_res
    }

@router.patch("/{cartera_id}")
def update_cartera(cartera_id: int, data: UpdateCarteraRequest, db: Session = Depends(get_db)):
    cartera = db.query(Cartera).options(joinedload(Cartera.operaciones)).filter(Cartera.id == cartera_id).first()
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
                
                cuotas_ids = [op.cuota_id for op in cartera.operaciones]
                if cuotas_ids:
                    db.query(Cuota).filter(Cuota.id.in_(cuotas_ids)).update(
                        {"estado_cesion": EstadoCuotaCedida.PENDIENTE},
                        synchronize_session=False
                    )
            elif nuevo_estado_str == "PENDIENTE":
                pass
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

@router.get("/{cartera_id}/export")
def export_cartera(cartera_id: int, db: Session = Depends(get_db)):
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
    sell_manager = PortfolioSell(db)
    sell_manager.cartera = cartera
    sell_manager.fetch_installments_from_cartera(cartera_id)
    
    if sell_manager.df_cuotas_venta is None or sell_manager.df_cuotas_venta.empty:
        raise HTTPException(status_code=400, detail="La cartera no tiene cuotas asociadas.")
        
    try:
        zip_path = sell_manager.export()
        return FileResponse(zip_path, media_type="application/zip", filename=os.path.basename(zip_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exportando: {str(e)}")

@router.delete("/{cartera_id}")
def delete_cartera(cartera_id: int, db: Session = Depends(get_db)):
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
    if cartera.estado != EstadoCartera.PENDIENTE:
        raise HTTPException(status_code=400, detail="No se puede eliminar una cartera que ya está CONFIRMADA (VENDIDA o COMPRADA).")
        
    try:
        if cartera.tipo_operacion == TipoOperacionCartera.COMPRA:
            from src.database.models import Cobranza, TipoCobranzaEnum
            has_cobranzas = db.query(Cobranza).join(Cuota).join(Credito).filter(
                Credito.cartera_id == cartera_id,
                Cobranza.tipo_cobranza != TipoCobranzaEnum.CNC.value
            ).first()
            if has_cobranzas:
                raise HTTPException(status_code=400, detail="No se puede eliminar la cartera porque tiene cobranzas asociadas y debería estar confirmada.")
                
            db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).delete(synchronize_session=False)
            
            creditos_asociados = db.query(Credito).filter(Credito.cartera_id == cartera_id).all()
            creditos_ids = [c.id for c in creditos_asociados]
            clientes_cuils = {cred.cliente_cuil for cred in creditos_asociados if cred.cliente_cuil}
            
            if creditos_ids:
                cuotas = db.query(Cuota).filter(Cuota.credito_id.in_(creditos_ids)).all()
                cuotas_ids = [c.id for c in cuotas]
                
                if cuotas_ids:
                    from src.database.models import Cobranza
                    db.query(Cobranza).filter(Cobranza.cuota_id.in_(cuotas_ids)).delete(synchronize_session=False)
                
                db.query(Cuota).filter(Cuota.credito_id.in_(creditos_ids)).delete(synchronize_session=False)
                db.query(Credito).filter(Credito.cartera_id == cartera_id).delete(synchronize_session=False)
                
            from sqlalchemy import or_
            for cuil in clientes_cuils:
                otros = db.query(Credito).filter(
                    Credito.cliente_cuil == cuil,
                    or_(Credito.cartera_id != cartera_id, Credito.cartera_id.is_(None))
                ).first()
                if not otros:
                    db.query(Cliente).filter(Cliente.cuil == cuil).delete(synchronize_session=False)
            
        else:
            if hasattr(cartera, "liquidaciones") and len(cartera.liquidaciones) > 0:
                raise HTTPException(status_code=400, detail="No se puede eliminar la cartera porque tiene liquidaciones asociadas y debería estar confirmada.")
                
            operaciones = db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).all()
            cuota_ids = [op.cuota_id for op in operaciones]
    
            if cuota_ids:
                db.query(Cuota).filter(Cuota.id.in_(cuota_ids)).update(
                    {"estado_cesion": EstadoCuotaCedida.NO_VENDIDA},
                    synchronize_session=False
                )
    
            db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).delete(synchronize_session=False)

        db.delete(cartera)
        db.commit()
        return {"status": "success", "message": f"Cartera {cartera_id} eliminada correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se puede eliminar la cartera (puede estar referenciada). Error: {str(e)}")

@router.get("/{cartera_id}/legajos/export")
def export_cartera_legajos(cartera_id: int, db: Session = Depends(get_db)):
    cartera = db.query(Cartera).filter(Cartera.id == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
    creditos_ids = set()
    if cartera.tipo_operacion == TipoOperacionCartera.COMPRA:
        creditos = db.query(Credito).filter(Credito.cartera_id == cartera_id).all()
        for c in creditos:
            creditos_ids.add(c.id)
    else:
        operaciones = db.query(OperacionCartera).filter(OperacionCartera.cartera_id == cartera_id).all()
        if operaciones:
            cuotas_ids = [op.cuota_id for op in operaciones]
            cuotas = db.query(Cuota).filter(Cuota.id.in_(cuotas_ids)).all()
            for c in cuotas:
                creditos_ids.add(c.credito_id)

    if not creditos_ids:
        raise HTTPException(status_code=400, detail="La cartera no tiene créditos asociados.")
        
    creditos = db.query(Credito).filter(Credito.id.in_(creditos_ids)).all()
    
    temp_dir = tempfile.mkdtemp()
    tna = float(cartera.tna_descuento) if cartera.tna_descuento is not None else 0.0
    socio_nombre = cartera.socio.razon_social if cartera.socio else "SinSocio"
    default_name = f"Legajos - Cartera Nro. {str(cartera.id).zfill(2)} - {socio_nombre} - {cartera.fecha_compra} - {tna:.2%}.zip"
    zip_path = os.path.join(temp_dir, default_name.replace("/", "-").replace(":", "-"))
    
    errores = []
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for credito in creditos:
            try:
                pdf_io = _merge_uploaded_docs_for_credito(credito.id, db)
                id_ext = f"{credito.id_externo} - " if credito.id_externo else ""
                nombre_pdf = f"Legajo Nro. {credito.id} - {id_ext}{credito.cliente_cuil}.pdf"
                
                # Create a temporary file to save the BytesIO content before adding to zip
                temp_pdf_path = os.path.join(temp_dir, nombre_pdf)
                with open(temp_pdf_path, "wb") as f:
                    f.write(pdf_io.getvalue())
                    
                zipf.write(temp_pdf_path, nombre_pdf)
                os.remove(temp_pdf_path)
            except Exception as e:
                errores.append(f"Credito ID {credito.id} (CUIL: {credito.cliente_cuil}): {str(e)}")
                
        if errores:
            errors_path = os.path.join(temp_dir, "errores.txt")
            with open(errors_path, "w") as f:
                f.write("Errores durante la generacion de legajos:\n")
                for err in errores:
                    f.write(f"- {err}\n")
            zipf.write(errors_path, "errores.txt")
            
    return FileResponse(zip_path, media_type="application/zip", filename=os.path.basename(zip_path))
