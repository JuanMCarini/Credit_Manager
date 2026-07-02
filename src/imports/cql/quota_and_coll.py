"""
Quota and Collection Import Module
==================================
This module handles the extraction, transformation, and load (ETL) of quotas 
and collections. It prevents memory bloat by performing selective SQL queries
using `IN` clauses instead of loading full tables.
It uses `bulk_insert_mappings` for Quotas (fast and safe), and chunked 
`add_all` for Collections to ensure SQLAlchemy's rounding adjustment triggers run correctly.
"""

import pandas as pd
import numpy as np
from src.database import engine, SessionLocal, Credito, Cuota, EstadoCuota
from src.database import TipoCobranzaEnum, Cobranza
from src.database.models.cobranzas import Proceso, TipoProcesoEnum

    # --- A. OPTIMIZED QUOTA LOAD AND MERGE ---
from src.imports.cql.read import CQLData

def import_quotas_and_coll(data: CQLData):
    df_cuotas = data.df_cuotas.copy()
    df_inventario = data.df_inventario.copy()

    # Fetch the External Key from df_inventario
    df_cuotas = df_cuotas.merge(
        df_inventario[['Clave Externa']], 
        left_on="Crédito", 
        right_on="Id. Op.", 
        how="left"
    )

    # Filter rows without External Key to avoid breaking relations
    df_cuotas = df_cuotas.dropna(subset=['Clave Externa'])
    df_cuotas['Clave Externa'] = df_cuotas['Clave Externa'].astype(str).str.strip()

    claves_externas = df_cuotas['Clave Externa'].unique().tolist()

    # 1. MEMORY OPTIMIZATION: Load IDs only for the involved credits
    with SessionLocal() as db:
        creditos_map = dict(
            db.query(Credito.id_externo, Credito.id)
              .filter(Credito.id_externo.in_(claves_externas))
              .all()
        )

    df_cuotas["credito_id"] = df_cuotas['Clave Externa'].map(creditos_map)

    # Filter quotas that do not have a credit in the database (security fallback)
    df_cuotas = df_cuotas.dropna(subset=['credito_id'])
    df_cuotas["credito_id"] = df_cuotas["credito_id"].astype(int)

    # --- B. QUOTA VECTORIZATION ---
    df_cuotas['Cuota_num'] = pd.to_numeric(df_cuotas['Cuota'], errors='coerce').fillna(0).astype(int)
    df_cuotas['Vto_ts'] = pd.to_datetime(df_cuotas['Vto.'], errors='coerce')
    for col in ["CA", "IN", "IV"]:
        df_cuotas[f"{col}_num"] = pd.to_numeric(df_cuotas[col], errors='coerce').fillna(0.0)

    # --- C. CHUNKED QUOTA INSERTION ---
    CHUNK_SIZE = 10000

    with SessionLocal() as db:
        try:
            # Set of quotas that already exist for this batch of credits to avoid duplicates
            creditos_ids = df_cuotas['credito_id'].unique().tolist()
            existing_cuotas = set(
                db.query(Cuota.credito_id, Cuota.nro_cuota)
                  .filter(Cuota.credito_id.in_(creditos_ids))
                  .all()
            )
        
            for start_idx in range(0, len(df_cuotas), CHUNK_SIZE):
                chunk_df = df_cuotas.iloc[start_idx:start_idx + CHUNK_SIZE]
                chunk_mappings = []
            
                chunk_dicts = chunk_df.to_dict('records')
                for row in chunk_dicts:
                    c_id = row["credito_id"]
                    n_cuota = row["Cuota_num"]
                
                    cuota_key = (c_id, n_cuota)
                    if cuota_key in existing_cuotas:
                        continue
                
                    existing_cuotas.add(cuota_key)
                
                    f_vto = row['Vto_ts'].date() if pd.notna(row['Vto_ts']) else None
                
                    mapping = {
                        "credito_id": c_id,
                        "nro_cuota": n_cuota,
                        "fecha_vencimiento": f_vto,
                        "capital": float(row["CA_num"]),
                        "interes": float(row["IN_num"]),
                        "iva": float(row["IV_num"])
                    }
                    chunk_mappings.append(mapping)
            
                if chunk_mappings:
                    # Quota has no ORM events, bulk_insert_mappings is safe and fast
                    db.bulk_insert_mappings(Cuota, chunk_mappings)
                    db.commit()
                
        except Exception as e:
            db.rollback()
            raise e


    # --- D. OPTIMIZED COLLECTION LOAD AND MERGE ---
    df_cobranzas = data.df_cobranzas.copy()

    # Remove advances that are of line "ANTICIPO"
    mask_anticipo = (df_cobranzas["Tipo Cobranza"] == "ANTICIPO") & (df_cobranzas["Línea"] == "ANTICIPO")
    df_cobranzas = df_cobranzas.loc[~mask_anticipo]

    df_cobranzas = df_cobranzas.merge(
        df_inventario[['Clave Externa']], 
        left_on="Crédito", 
        right_on="Id. Op.", 
        how="left"
    )

    # Map to credito_id using the same optimized map we already loaded
    df_cobranzas['Clave Externa'] = df_cobranzas['Clave Externa'].astype(str).str.strip()
    df_cobranzas["credito_id"] = df_cobranzas["Clave Externa"].map(creditos_map)

    # Remove PENALTY with null credit
    mask_null_penalty = df_cobranzas["credito_id"].isna() & (df_cobranzas["Línea"] == "PENALTY")
    df_cobranzas = df_cobranzas.loc[~mask_null_penalty]

    if not df_cobranzas[df_cobranzas["credito_id"].isna()].empty:
        print("Mostrando DataFrame sin creditor_id:")
        print(df_cobranzas[df_cobranzas["credito_id"].isna()])
        raise ValueError("No credits found for the displayed collections")

    df_cobranzas["credito_id"] = df_cobranzas["credito_id"].astype(int)

    # 2. MEMORY OPTIMIZATION FOR QUOTAS IN COLLECTIONS:
    # Query DB only for the real IDs of recently inserted or existing quotas
    # associated with the credits in this batch
    with SessionLocal() as db:
        cobs_cred_ids = df_cobranzas["credito_id"].unique().tolist()
        cuotas_necesarias = db.query(Cuota.id, Cuota.credito_id, Cuota.nro_cuota)\
                              .filter(Cuota.credito_id.in_(cobs_cred_ids))\
                              .all()

    df_cuotas_mini = pd.DataFrame(cuotas_necesarias, columns=["cuota_id", "credito_id", "nro_cuota"])

    df_cobranzas['Cta_num'] = pd.to_numeric(df_cobranzas['Cta.'], errors='coerce').fillna(0).astype(int)

    # Perform an ultra-fast local merge to get the true cuota_id from the database
    df_cobranzas = df_cobranzas.merge(
        df_cuotas_mini,
        left_on=["credito_id", "Cta_num"],
        right_on=["credito_id", "nro_cuota"],
        how="left"
    ).drop(columns=["nro_cuota"])

    # Ignore collections where the cuota_id could not be found
    df_cobranzas = df_cobranzas.dropna(subset=["cuota_id"])
    df_cobranzas["cuota_id"] = df_cobranzas["cuota_id"].astype(int)

    # --- E. COLLECTION VECTORIZATION ---
    for col in ["CA", "IN", "IV", "TOTAL"]:
        df_cobranzas[col] = pd.to_numeric(df_cobranzas[col], errors='coerce').fillna(0.0).abs()

    df_cobranzas['Emisión_ts'] = pd.to_datetime(df_cobranzas['Emisión'], errors='coerce')

    tipos_cobranzas = {
        'ANTICIPO': TipoCobranzaEnum.ANTICIPO,
        'COBRANZA': TipoCobranzaEnum.COMUN,
        'COBRANZA X CANCEL ANT': TipoCobranzaEnum.BCA,
        'CUOTA NO COMPRADA': TipoCobranzaEnum.CNC,
        'RECIBO': TipoCobranzaEnum.AJUSTE
    }

    df_cobranzas["Tipo Cobranza Enum"] = df_cobranzas["Tipo Cobranza"].map(tipos_cobranzas)

    mask_penalty = df_cobranzas["Línea"] == "PENALTY"
    df_cobranzas.loc[mask_penalty, "Tipo Cobranza Enum"] = TipoCobranzaEnum.PENALTY

    mask_ca = (
        (df_cobranzas["Tipo Cobranza Enum"] == TipoCobranzaEnum.COMUN)
        & (df_cobranzas["CA"] != 0)
        & (df_cobranzas["IN"] == 0)
        & (df_cobranzas["IV"] == 0)
    )
    df_cobranzas.loc[mask_ca, "Tipo Cobranza Enum"] = TipoCobranzaEnum.CA

    # Default fallback if unmapped
    df_cobranzas["Tipo Cobranza Enum"] = df_cobranzas["Tipo Cobranza Enum"].fillna(TipoCobranzaEnum.COMUN)

    # --- F. COLLECTION INSERTION (SAFE FOR ORM EVENTS) ---
    with SessionLocal() as db:
        try:
            # 3. CREACIÓN DEL PROCESO MASIVO
            # Creamos la cabecera del lote para rastrear la carga y permitir su reversión.
            nuevo_proceso = Proceso(
                tipo=TipoProcesoEnum.MASIVO_CSV
            )
            db.add(nuevo_proceso)
            db.flush()  # Flushear para obtener el nuevo_proceso.id

            # We process in chunks to protect memory, but we use add_all()
            # instead of bulk_insert to ensure the SQLAlchemy rounding trigger works.
            for start_idx in range(0, len(df_cobranzas), CHUNK_SIZE):
                chunk_df = df_cobranzas.iloc[start_idx:start_idx + CHUNK_SIZE]
            
                collections = []
                chunk_dicts = chunk_df.to_dict('records')
            
                for row in chunk_dicts:
                    f_emision = row['Emisión_ts'].date() if pd.notna(row['Emisión_ts']) else None
                
                    new_coll = Cobranza(
                        cuota_id=row["cuota_id"],
                        proceso_id=nuevo_proceso.id,
                        tipo_cobranza=row["Tipo Cobranza Enum"],
                        capital=float(row["CA"]),
                        interes=float(row["IN"]),
                        iva=float(row["IV"]),
                        fecha=f_emision
                    )
                    collections.append(new_coll)
            
                if collections:
                    # add_all appends objects to session.new, allowing before_flush to iterate them
                    db.add_all(collections)
                    db.flush()
                    db.commit()

            print(f"✅ Se importaron {len(df_cuotas)} cuotas y {len(df_cobranzas)} cobranzas exitosamente.")

        except Exception as e:
            db.rollback()
            raise e