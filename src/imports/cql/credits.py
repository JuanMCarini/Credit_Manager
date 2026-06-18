"""
Credits Import Module
=====================
This module handles the extraction, transformation, and load (ETL) of credit data.
It merges credit and inventory datasets, computes the Annual Nominal Rate (TNA) 
vectorized via numpy_financial, resolves originators, and performs chunked bulk 
inserts into the database to optimize performance.
"""

import warnings
import pandas as pd
import numpy as np
import numpy_financial as npf
from sqlalchemy.orm import Session
from src.database import engine, SessionLocal, Credito
from src.database.models import EstadoCredito, TipoCredito
from . import read as read_files

# 1. Copy and merge datasets
df_creditos = read_files.df_creditos.copy()
df_inventario = read_files.df_inventario.copy()
df_creditos = df_creditos.merge(
    df_inventario[["Clave Externa", "CUIL"]], 
    left_index=True, 
    right_index=True, 
    how="left"
)
df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")

# --- 2. PANDAS AND NUMPY VECTORIZATION ---

# A. Clean CUIL
df_creditos['CUIL_clean'] = df_creditos['CUIL'].astype(str).str.replace(r'\D', '', regex=True).replace('', np.nan)

# B. External Key
df_creditos['Clave Externa_clean'] = df_creditos['Clave Externa'].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)

# Ignore rows without an external key (crucial for PK)
df_creditos = df_creditos.dropna(subset=['Clave Externa_clean'])

# C. Dates and Amounts
df_creditos['Emisión_ts'] = pd.to_datetime(df_creditos['Emisión'], errors='coerce')
df_creditos['Capital_num'] = pd.to_numeric(df_creditos['Capital'], errors='coerce').fillna(0.0)
df_creditos['Plazo_num'] = pd.to_numeric(df_creditos['Plazo'], errors='coerce').fillna(0).astype(int)
df_creditos['Imp. Cuota_num'] = pd.to_numeric(df_creditos['Imp. Cuota'], errors='coerce').fillna(0.0)

# D. TNA Vectorization with numpy_financial
valid_mask = (df_creditos['Plazo_num'] > 0) & (df_creditos['Capital_num'] > 0) & (df_creditos['Imp. Cuota_num'] > 0)

# Initialize all with 0.0
df_creditos['TNA_calc'] = 0.0

if valid_mask.any():
    # numpy_financial supports array-based calculations, but might raise a RuntimeWarning 
    # if the installment is too low causing the math formula to diverge. Safely ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        tasas_mensuales = npf.rate(
            nper=df_creditos.loc[valid_mask, 'Plazo_num'], 
            pmt=-df_creditos.loc[valid_mask, 'Imp. Cuota_num'], 
            pv=df_creditos.loc[valid_mask, 'Capital_num'], 
            fv=0
        )
    
    # Replace possible NaNs with 0
    tasas_mensuales = np.where(np.isnan(tasas_mensuales), 0.0, tasas_mensuales)
    tasas_mensuales = np.maximum(tasas_mensuales, 0.0)
    
    # Convert monthly rate to TNA
    df_creditos.loc[valid_mask, 'TNA_calc'] = tasas_mensuales * 365 / 30

# E. Vectorize Status
def map_estado_cred(val):
    if pd.isna(val): return EstadoCredito.APROBADO
    s = str(val).strip().upper()
    if "ACTIVO" in s: return EstadoCredito.ACTIVO
    if "MOROSO" in s or "MORA" in s: return EstadoCredito.MOROSO
    if "CANCELADO" in s or "CANCEL" in s: return EstadoCredito.CANCELADO
    return EstadoCredito.APROBADO

df_creditos['Estado_enum'] = df_creditos['Estado'].apply(map_estado_cred)

# F. Line -> Partner ID mapping optimization
# Process each unique line ONLY ONCE to avoid iterating over df_socios a million times
lineas_unicas = df_creditos["Línea"].dropna().astype(str).str.strip().str.upper().unique()
linea_socio_map = {}
linea_tipo_map = {}

for linea in lineas_unicas:
    if linea == "PENALTY":
        linea_socio_map[linea] = None
        linea_tipo_map[linea] = TipoCredito.PENALTY
    else:
        # Reverse substring search in df_socios
        matched_idx = None
        for socio_id, socio_row in df_socios.iterrows():
            rs = str(socio_row['razon_social']).upper() if pd.notna(socio_row['razon_social']) else ""
            if rs and rs in linea:
                matched_idx = socio_id
                break
                
        if matched_idx is not None:
            linea_socio_map[linea] = int(matched_idx)
            linea_tipo_map[linea] = TipoCredito.FRANCES
        else:
            raise ValueError(f'⚠️ "{linea}" not found in "socios_comerciales". Please add it first.')

df_creditos['Línea_clean'] = df_creditos["Línea"].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], np.nan)
df_creditos['socio_id'] = df_creditos['Línea_clean'].map(linea_socio_map)
# Replace NaN with None for DB compatibility
df_creditos['socio_id'] = df_creditos['socio_id'].replace({np.nan: None})
df_creditos['tipo_credito'] = df_creditos['Línea_clean'].map(linea_tipo_map)

# --- 3. CONTEXT MANAGER AND CHUNKED BULK INSERT ---
with SessionLocal() as db:
    try:
        CHUNK_SIZE = 10000
        
        for start_idx in range(0, len(df_creditos), CHUNK_SIZE):
            chunk_df = df_creditos.iloc[start_idx:start_idx + CHUNK_SIZE]
            
            # Query existing external_id combinations in DB (to avoid loading all)
            chunk_ext_ids = chunk_df['Clave Externa_clean'].unique().tolist()
            
            existing_credits = {
                (c.id_externo, c.socio_originador_id)
                for c in db.query(Credito.id_externo, Credito.socio_originador_id)
                         .filter(Credito.id_externo.in_(chunk_ext_ids))
                         .all()
            }

            chunk_mappings = []
            chunk_dicts = chunk_df.to_dict('records')
            
            for row in chunk_dicts:
                ext_id = row['Clave Externa_clean']
                socio_id = row['socio_id']
                
                # Local/DB uniqueness control
                credito_key = (ext_id, socio_id)
                if credito_key in existing_credits:
                    continue
                    
                existing_credits.add(credito_key)
                
                # Safe date extraction (avoiding pd.NaT)
                f_emision = row['Emisión_ts'].date() if pd.notna(row['Emisión_ts']) else None
                
                mapping = {
                    "id_externo": ext_id,
                    "cliente_cuil": row['CUIL_clean'] if pd.notna(row['CUIL_clean']) else None,
                    "socio_originador_id": int(socio_id) if socio_id is not None and pd.notna(socio_id) else None,
                    "capital": float(row['Capital_num']),
                    "plazo": int(row['Plazo_num']),
                    "tna_c_iva": float(row['TNA_calc']),
                    "fecha_emision": f_emision,
                    "estado": row['Estado_enum'],
                    "tipo_credito": row['tipo_credito'] if pd.notna(row['tipo_credito']) else TipoCredito.FRANCES
                }
                chunk_mappings.append(mapping)
                
            if chunk_mappings:
                db.bulk_insert_mappings(Credito, chunk_mappings)
                db.commit()
                
    except Exception as e:
        db.rollback()
        raise e