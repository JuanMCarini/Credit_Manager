import io
import zipfile
import unicodedata
from datetime import datetime, date
from typing import Optional

import pandas as pd
from sqlalchemy import text

from src.database import engine
from src.reports.balances import saldos

def normalize_text(text: str) -> str:
    if pd.isna(text):
        return "DESCONOCIDO"
    text = str(text).upper()
    text = text.replace("Ñ", "N")
    # Remove accents (e.g. Á -> A)
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.replace(";", "").strip()


def format_bcra_amount(amount: float) -> str:
    """Format amount to thousands of pesos (rounded)."""
    thousands = int(amount / 1000.0)
    return f"{thousands:012d}"


def apply_custom_filters(
    df: pd.DataFrame,
    origen: Optional[str] = None,
    socio_originador: Optional[str] = None,
    nro_orden: Optional[str] = None,
    sit_mora: Optional[str] = None,
    comprado: Optional[str] = None,  # "Ambas", "Propias", "Terceros"
) -> pd.DataFrame:
    
    if df.empty:
        return df

    if origen and origen != "Ambos":
        if "tipo_op" in df.columns:
            if origen == "Comprados":
                df = df[df["tipo_op"] == "COMPRA"]
            elif origen == "Propios":
                df = df[df["tipo_op"] != "COMPRA"]

    if socio_originador and socio_originador != "Todos" and socio_originador.strip():
        df = df[df["Originador"] == socio_originador]

    # Nro de orden is a metadata field for the presentation, not a filter for Credit ID.

    return df


def calculate_arrears_and_situation(df: pd.DataFrame, fecha_corte: datetime) -> pd.DataFrame:
    """
    Calculate dias de atraso and assign BCRA situation.
    """
    if df.empty:
        df["dias_atraso"] = 0
        return df
        
    df["dias_atraso"] = (fecha_corte - pd.to_datetime(df["Fecha Vencimiento"])).dt.days
    df.loc[df["dias_atraso"] < 0, "dias_atraso"] = 0
    return df


def assign_bcra_situation(dias: int) -> str:
    if dias <= 31:
        return "01"
    elif dias <= 90:
        return "21"
    elif dias <= 180:
        return "03"
    elif dias <= 365:
        return "04"
    else:
        return "05"



def _get_bcra_aggregated_data(
    fecha_corte: date,
    vto_hasta: Optional[date] = None,
    origen: Optional[str] = None,
    socio_originador: Optional[str] = None,
    nro_orden: Optional[str] = None,
    sit_mora: Optional[str] = None,
    comprado: Optional[str] = None,
    min_monto_mora: Optional[float] = None,
    tipo_reporte: Optional[str] = "NORMAL",
    cliente: Optional[str] = None,
):
    dt_corte = datetime.combine(fecha_corte, datetime.min.time())
    
    propias = None
    if comprado == "Propias":
        propias = True
    elif comprado == "Terceros":
        propias = False
        
    df = saldos(fecha=dt_corte, con_saldo=True, propias=propias)
    df = df.reset_index()
    df = apply_custom_filters(df, origen, socio_originador, nro_orden, None, comprado)

    if tipo_reporte == "RECTIFICATORIO" and cliente and cliente.strip():
        cid = cliente.strip()
        with engine.connect() as conn:
            try:
                int_cid = int(cid)
                where_clause = "id = :int_cid OR cuil = :cid OR dni = :cid"
                params = {"int_cid": int_cid, "cid": cid}
            except ValueError:
                where_clause = "cuil = :cid OR dni = :cid"
                params = {"cid": cid}
                
            res = conn.execute(text(f"SELECT cuil FROM clientes WHERE {where_clause}"), params).fetchall()
            matching_cuils = [r[0] for r in res]
            
        if matching_cuils:
            df = df[df["CUIL Cliente"].isin(matching_cuils)]
        else:
            return pd.DataFrame(), None

    
    if vto_hasta:
        dt_vto = datetime.combine(vto_hasta, datetime.min.time())
        df = df[pd.to_datetime(df["Fecha Emisión"]) <= dt_vto]

    df = calculate_arrears_and_situation(df, dt_corte)
    
    df["Importe_BCRA"] = df.apply(
        lambda row: row["Total"] if row["dias_atraso"] > 0 else row["Capital"], 
        axis=1
    )
    
    if df.empty:
        return pd.DataFrame(), None
        
    # Fetch client names
    cuils = df["CUIL Cliente"].dropna().unique().tolist()
    if cuils:
        cuils_str = ",".join(f"'{c}'" for c in cuils)
        clientes_query = text(f"SELECT cuil, apellido, nombre FROM clientes WHERE cuil IN ({cuils_str})")
        df_clientes = pd.read_sql_query(clientes_query, engine)
        df_clientes["Nombre Completo"] = df_clientes["apellido"] + " " + df_clientes["nombre"]
        df_clientes["Nombre Completo"] = df_clientes["Nombre Completo"].apply(normalize_text)
        df = df.merge(df_clientes[["cuil", "Nombre Completo"]], left_on="CUIL Cliente", right_on="cuil", how="left")
    else:
        df["Nombre Completo"] = "DESCONOCIDO"

    # Aggregate by Client
    agg_df = df.groupby("CUIL Cliente").agg(
        Total_Deuda=("Importe_BCRA", "sum"),
        Max_Dias_Atraso=("dias_atraso", "max"),
        Nombre=("Nombre Completo", "first")
    ).reset_index()

    agg_df["Situacion"] = agg_df["Max_Dias_Atraso"].apply(assign_bcra_situation)
    
    if sit_mora and sit_mora != "Todas" and str(sit_mora).strip():
        agg_df = agg_df[agg_df["Situacion"] == str(sit_mora).strip()]

    if min_monto_mora is not None:
        agg_df = agg_df[agg_df["Total_Deuda"] >= min_monto_mora]

    # Get TNA
    min_tna_val = None
    credito_ids = df["ID Credito"].dropna().unique().tolist()
    if credito_ids:
        ids_str = ",".join(str(int(c)) for c in credito_ids)
        min_tna_query = text(f"SELECT MIN(tna_c_iva) FROM creditos WHERE id IN ({ids_str}) AND tna_c_iva > 0")
        with engine.connect() as conn:
            min_tna_val = conn.execute(min_tna_query).scalar()
            if min_tna_val is None:
                min_tna_val = conn.execute(text("SELECT MIN(tna_c_iva) FROM creditos WHERE tna_c_iva > 0")).scalar()
                
    return agg_df, min_tna_val

def generate_bcra_files(
    fecha_corte: date,
    vto_hasta: Optional[date] = None,
    origen: Optional[str] = None,
    socio_originador: Optional[str] = None,
    nro_orden: Optional[str] = None,
    sit_mora: Optional[str] = None,
    comprado: Optional[str] = None,
    min_monto_mora: Optional[float] = None,
    tipo_reporte: Optional[str] = "NORMAL",
    cliente: Optional[str] = None,
) -> bytes:
    agg_df, min_tna_val = _get_bcra_aggregated_data(
        fecha_corte, vto_hasta, origen, socio_originador, nro_orden, sit_mora, comprado, min_monto_mora, tipo_reporte, cliente
    )
    
    if agg_df.empty:
        return _create_zip("", "", "0;000,00\r\n")

    proveedores_lines = []
    importes_lines = []
    
    for _, row in agg_df.iterrows():
        cuil = str(row["CUIL Cliente"]).replace("-", "").strip()
        nombre = str(row["Nombre"])
        sit = row["Situacion"]
        total_miles = format_bcra_amount(row["Total_Deuda"])
        
        nombre_padded = nombre.ljust(55)[:55]
        total_miles_proveedores = str(total_miles).zfill(14)
        total_miles_importes = str(total_miles).zfill(12)
        
        proveedores_lines.append(f"11;{cuil};{nombre_padded};{sit};{total_miles_proveedores};0;0;0000;00")
        importes_lines.append(f"11;{cuil};09;{total_miles_importes}")

    proveedores_txt = "\r\n".join(proveedores_lines) + "\r\n"
    importes_txt = "\r\n".join(importes_lines) + "\r\n"
    
    if min_tna_val is not None:
        tna_formatted = f"{min_tna_val * 100:06.2f}".replace(".", ",")
        tasa_txt = f"1;{tna_formatted}\r\n"
    else:
        tasa_txt = "1;000,00\r\n"
        
    return _create_zip(proveedores_txt, importes_txt, tasa_txt)


def _create_zip(proveedores: str, importes: str, tasa: str) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("PROVEEDORES.TXT", proveedores.encode('cp1252', errors='replace'))
        zip_file.writestr("IMPORTES.TXT", importes.encode('cp1252', errors='replace'))
        zip_file.writestr("TASA.TXT", tasa.encode('cp1252', errors='replace'))
    return zip_buffer.getvalue()


def generar_reporte_personalizado_excel(
    fecha_corte: date,
    vto_hasta: Optional[date] = None,
    origen: Optional[str] = None,
    socio_originador: Optional[str] = None,
    nro_orden: Optional[str] = None,
    sit_mora: Optional[str] = None,
    comprado: Optional[str] = None,
    min_monto_mora: Optional[float] = None,
    tipo_reporte: Optional[str] = "NORMAL",
    cliente: Optional[str] = None,
) -> io.BytesIO:
    agg_df, min_tna_val = _get_bcra_aggregated_data(
        fecha_corte, vto_hasta, origen, socio_originador, nro_orden, sit_mora, comprado, min_monto_mora, tipo_reporte, cliente
    )
    
    proveedores_data = []
    importes_data = []
    
    if not agg_df.empty:
        for _, row in agg_df.iterrows():
            cuil = str(row["CUIL Cliente"]).replace("-", "").strip()
            nombre = str(row["Nombre"])
            sit = row["Situacion"]
            total_miles = format_bcra_amount(row["Total_Deuda"])
            
            nombre_padded = nombre.ljust(55)[:55]
            total_miles_proveedores = str(total_miles).zfill(14)
            total_miles_importes = str(total_miles).zfill(12)
            
            proveedores_data.append({
                "Tipo Id": "11",
                "Nro Id": cuil,
                "Nombre": nombre_padded,
                "Situacion": sit,
                "Importe": total_miles_proveedores,
                "Encuadramiento Art 26": "0",
                "Recategorizacion": "0",
                "Dias Atraso": "0000",
                "Sit sin reclasif": "00"
            })
            
            importes_data.append({
                "Tipo Id": "11",
                "Nro Id": cuil,
                "Tipo Asistencia": "09",
                "Importe": total_miles_importes
            })
            
    tasa_data = []
    if agg_df.empty:
        tasa_data.append({"Tipo": "0", "TNA": "000,00"})
    else:
        if min_tna_val is not None:
            tna_formatted = f"{min_tna_val * 100:06.2f}".replace(".", ",")
            tasa_data.append({"Tipo": "1", "TNA": tna_formatted})
        else:
            tasa_data.append({"Tipo": "1", "TNA": "000,00"})
            
    df_prov = pd.DataFrame(proveedores_data)
    df_imp = pd.DataFrame(importes_data)
    df_tasa = pd.DataFrame(tasa_data)

    # If DataFrames are empty, ensure they still have columns
    if df_prov.empty:
        df_prov = pd.DataFrame(columns=["Tipo Id", "Nro Id", "Nombre", "Situacion", "Importe", "Encuadramiento Art 26", "Recategorizacion", "Dias Atraso", "Sit sin reclasif"])
    if df_imp.empty:
        df_imp = pd.DataFrame(columns=["Tipo Id", "Nro Id", "Tipo Asistencia", "Importe"])
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_prov.to_excel(writer, index=False, sheet_name='PROVEEDORES')
        df_imp.to_excel(writer, index=False, sheet_name='IMPORTES')
        df_tasa.to_excel(writer, index=False, sheet_name='TASA')
    output.seek(0)
    return output
