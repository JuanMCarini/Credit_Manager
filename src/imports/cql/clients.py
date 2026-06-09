"""
Clients Import Module
=====================
This module handles the extraction, transformation, and load (ETL) of client data.
It merges client inventory information, cleans up unique identifiers (CUIL, DNI),
normalizes statuses and nationalities, and performs bulk inserts in chunks to 
efficiently load data into the database while avoiding memory exhaustion.
"""

import pandas as pd
import numpy as np
from src.database import SessionLocal, Cliente, SexoEnum, EstadoClienteEnum, Provincia, Empleador, SocioComercial
# pyrefly: ignore [missing-import]
from .read import df_clientes, df_inventario

# 1. Group df_inventario to prevent 1-to-many duplication (1 row per client)
df_inventario_grouped = df_inventario.groupby("Id. Cliente")[["Org.", "Sueldo Liquido", "Línea"]].first()

# 2. Perform a clean merge without duplicated rows
df_clientes = df_clientes.merge(
    df_inventario_grouped, 
    left_index=True, 
    right_index=True, 
    how="left"
)

# 3. Remove duplicates in df_clientes (by CUIL and by DNI)
df_clientes = df_clientes.drop_duplicates(subset=['C.U.I.L.']).drop_duplicates(subset=['D.N.I.'])

# Function to unify and normalize nationality values
def normalize_nacionalidad(val):
    if pd.isna(val):
        return None
    val = str(val).strip().upper()
    if val.startswith("ARG") or val == "AR" or "ARGENTIN" in val:
        return "ARGENTINA"
    if val.startswith("URU") or "URUGUAY" in val:
        return "URUGUAYA"
    if val.startswith("PAR") or "PARAGUAY" in val:
        return "PARAGUAYA"
    if val.startswith("BOL") or "BOLIVIA" in val:
        return "BOLIVIANA"
    if val.startswith("CHI") or "CHILE" in val:
        return "CHILENA"
    if val.startswith("BRA") or val.startswith("BR") or "BRASIL" in val:
        return "BRASILEÑA"
    return val

# --- 1. PANDAS VECTORIZATION ---
# Clean identifiers by removing non-numeric characters
df_clientes['C.U.I.L._clean'] = df_clientes['C.U.I.L.'].astype(str).str.replace(r'\D', '', regex=True).replace('', np.nan)
df_clientes['D.N.I._clean'] = df_clientes['D.N.I.'].astype(str).str.replace(r'\D', '', regex=True).replace('', np.nan)

if 'CBU' in df_clientes.columns:
    df_clientes['CBU_clean'] = df_clientes['CBU'].astype(str).str.replace(r'\D', '', regex=True).replace('', np.nan)
else:
    df_clientes['CBU_clean'] = np.nan

# Ignore rows without valid CUIL or DNI from the beginning
df_clientes = df_clientes.dropna(subset=['C.U.I.L._clean', 'D.N.I._clean'])

# Vectorized mappings
sexo_map = {
    'M': SexoEnum.MASCULINO, 'MASCULINO': SexoEnum.MASCULINO, '1': SexoEnum.MASCULINO,
    'F': SexoEnum.FEMENINO, 'FEMENINO': SexoEnum.FEMENINO, '2': SexoEnum.FEMENINO
}
def map_sexo(val):
    if pd.isna(val): return None
    s = str(val).strip().upper()
    return sexo_map.get(s, SexoEnum.OTRO if s else None)

estado_map = {
    'ACTIVO': EstadoClienteEnum.ACTIVO,
    'MOROSO': EstadoClienteEnum.MOROSO,
    'INCOBRABLE': EstadoClienteEnum.INCOBRABLE,
    'INACTIVO': EstadoClienteEnum.INACTIVO,
}
def map_estado(val):
    if pd.isna(val): return None
    s = str(val).strip().upper()
    return estado_map.get(s)

df_clientes['SEXO_enum'] = df_clientes['SEXO'].apply(map_sexo) if 'SEXO' in df_clientes.columns else None
df_clientes['ESTADO_enum'] = df_clientes['ESTADO'].apply(map_estado) if 'ESTADO' in df_clientes.columns else None
df_clientes['NACIONALIDAD_norm'] = df_clientes['NACIONALIDAD'].apply(normalize_nacionalidad) if 'NACIONALIDAD' in df_clientes.columns else None

# Dates handling
if 'FECHA NACIMIENTO' in df_clientes.columns:
    df_clientes['FECHA NACIMIENTO_ts'] = pd.to_datetime(df_clientes['FECHA NACIMIENTO'], errors='coerce')
else:
    df_clientes['FECHA NACIMIENTO_ts'] = pd.NaT

if 'FECHA ESTADO' in df_clientes.columns:
    df_clientes['FECHA ESTADO_ts'] = pd.to_datetime(df_clientes['FECHA ESTADO'], errors='coerce')
else:
    df_clientes['FECHA ESTADO_ts'] = pd.NaT

# Convert numerical types
if 'Sueldo Liquido' in df_clientes.columns:
    df_clientes['Sueldo Liquido_num'] = pd.to_numeric(df_clientes['Sueldo Liquido'], errors='coerce').fillna(0.0)
else:
    df_clientes['Sueldo Liquido_num'] = 0.0

if 'CALLE NÚMERO' in df_clientes.columns:
    # Extract first block of numbers for cases like "25 - A" or "123B"
    extracted_numbers = df_clientes['CALLE NÚMERO'].astype(str).str.extract(r'(\d+)')[0]
    df_clientes['CALLE NÚMERO_num'] = pd.to_numeric(extracted_numbers, errors='coerce').fillna(0).astype(int)
else:
    df_clientes['CALLE NÚMERO_num'] = 0

# --- 2. DATABASE CONTEXT MANAGER USAGE ---
with SessionLocal() as db:
    try:
        # Load general maps that are small enough to fit in memory
        provincia_map = {p.nombre.upper().strip(): p.id for p in db.query(Provincia).all()}
        empleadores_map = {e.razon_social: e.id for e in db.query(Empleador).all()}

        # Register new employers detected in 'Org.'
        if "Org." in df_clientes.columns:
            orgs_unicos = df_clientes["Org."].dropna().unique()
            
            # Map each unique Org to a socio_id using its Línea
            org_socio_id = {}
            if "Línea" in df_clientes.columns:
                socios = db.query(SocioComercial).all()
                org_linea = df_clientes.groupby("Org.")["Línea"].first().to_dict()
                for org, linea in org_linea.items():
                    if pd.isna(linea):
                        org_socio_id[org] = None
                        continue
                    l_upper = str(linea).upper()
                    matched_id = None
                    for s in socios:
                        if s.razon_social and str(s.razon_social).upper() in l_upper:
                            matched_id = s.id
                            break
                    org_socio_id[org] = matched_id

            for org in orgs_unicos:
                org_clean = str(org).strip().upper()
                if org_clean and org_clean not in empleadores_map:
                    nuevo_emp = Empleador(
                        razon_social=org_clean,
                        socio_comercial_id=org_socio_id.get(org)
                    )
                    db.add(nuevo_emp)
                    db.flush()
                    empleadores_map[org_clean] = nuevo_emp.id

        # --- 3. CHUNK PROCESSING ---
        CHUNK_SIZE = 10000
        
        for start_idx in range(0, len(df_clientes), CHUNK_SIZE):
            chunk_df = df_clientes.iloc[start_idx:start_idx + CHUNK_SIZE]
            
            # Query existing CUILs and DNIs ONLY for this chunk to save memory
            chunk_cuils = chunk_df['C.U.I.L._clean'].unique().tolist()
            chunk_docs = chunk_df['D.N.I._clean'].unique().tolist()
            
            existing_cuils = {c[0] for c in db.query(Cliente.cuil).filter(Cliente.cuil.in_(chunk_cuils)).all()}
            existing_docs = {c[0] for c in db.query(Cliente.documento).filter(Cliente.documento.in_(chunk_docs)).all()}

            chunk_mappings = []
            
            # Convert to dictionary list for fast iteration
            chunk_dicts = chunk_df.to_dict('records')
            
            for row in chunk_dicts:
                cuil_clean = row['C.U.I.L._clean']
                doc_clean = row['D.N.I._clean']
                
                # Ignore if missing key data
                if pd.isna(cuil_clean) or pd.isna(doc_clean): 
                    continue
                # Ignore if already exists in DB
                if cuil_clean in existing_cuils or doc_clean in existing_docs: 
                    continue
                
                # Prevent duplicate collisions within the same chunk
                existing_cuils.add(cuil_clean)
                existing_docs.add(doc_clean)
                
                prov_name = str(row['PROVINCIA']).strip().upper() if pd.notna(row.get('PROVINCIA')) else None
                emp_name = str(row['Org.']).strip().upper() if pd.notna(row.get('Org.')) else None
                
                cbu_clean = row['CBU_clean'] if pd.notna(row.get('CBU_clean')) else None
                calle_nro = row['CALLE NÚMERO_num'] if row.get('CALLE NÚMERO_num', 0) > 0 else None
                
                # Extract dates with safe handling of NaT
                f_nac = row['FECHA NACIMIENTO_ts'].date() if pd.notna(row.get('FECHA NACIMIENTO_ts')) else None
                f_est = row['FECHA ESTADO_ts'].date() if pd.notna(row.get('FECHA ESTADO_ts')) else None
                
                mapping = {
                    "cuil": cuil_clean,
                    "documento": doc_clean,
                    "apellido": str(row['APELLIDO']).strip().upper() if pd.notna(row.get('APELLIDO')) else "",
                    "nombre": str(row['NOMBRE']).strip().upper() if pd.notna(row.get('NOMBRE')) else "",
                    "fecha_nacimiento": f_nac,
                    "sexo": row.get('SEXO_enum'),
                    "estado_civil": str(row['ESTADO CIVIL']).strip().upper() if pd.notna(row.get('ESTADO CIVIL')) else None,
                    "nacionalidad": row.get('NACIONALIDAD_norm'),
                    "legajo": str(row['LEGAJO']).strip() if pd.notna(row.get('LEGAJO')) else None,
                    "estado": row.get('ESTADO_enum'),
                    "fecha_estado": f_est,
                    "cbu": cbu_clean,
                    "calle": str(row['CALLE']).strip() if pd.notna(row.get('CALLE')) else None,
                    "calle_nro": calle_nro,
                    "piso": str(row['PISO']).strip() if pd.notna(row.get('PISO')) else None,
                    "depto": str(row['DEPTO.']).strip() if pd.notna(row.get('DEPTO.')) else None,
                    "id_provincia": provincia_map.get(prov_name),
                    "id_codigo_postal": str(row['CÓDIGO POSTAL']).strip() if pd.notna(row.get('CÓDIGO POSTAL')) else None,
                    "localidad": str(row['LOCALIDAD']).strip().upper() if pd.notna(row.get('LOCALIDAD')) else None,
                    "telefono": str(row['TELÉFONO']).strip() if pd.notna(row.get('TELÉFONO')) else None,
                    "telefono_2": str(row['CELULAR']).strip() if pd.notna(row.get('CELULAR')) else None,
                    "mail": str(row['E-MAIL']).strip() if pd.notna(row.get('E-MAIL')) else None,
                    "remuneracion": row.get('Sueldo Liquido_num', 0.0),
                    "empleador_id": empleadores_map.get(emp_name) if emp_name else None
                }
                chunk_mappings.append(mapping)
                
            # Insert valid records from this chunk
            if chunk_mappings:
                db.bulk_insert_mappings(Cliente, chunk_mappings)
                db.commit()  # Commit current chunk to ensure persistence
                
    except Exception as e:
        db.rollback()
        raise e