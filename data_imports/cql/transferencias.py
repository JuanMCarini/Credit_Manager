import pandas as pd
from sqlalchemy.orm import Session
from src.database import engine, SessionLocal
from src.database.models import Credito, Transferencia

def import_transferencias(cql_data):
    """
    Importa un DataFrame de transferencias a la base de datos.
    El DataFrame debe contener las siguientes columnas (luego de los ajustes):
    ['CBU', 'monto', 'CUIT', 'credito_id', 'razon_social']
    """
    df = cql_data.df_transferencias.copy()

    with SessionLocal() as db:
        try:
            # 1. Obtener mapeo de id_externo -> Credito.id desde la BD
            creditos_db = db.query(Credito.id, Credito.id_externo).all()
            ext_to_internal_id = {c.id_externo: c.id for c in creditos_db if c.id_externo}

            # 2. Mapear el ID externo en el DataFrame al ID interno de la BD
            df['credito_id_str'] = df['credito_id'].astype(str).str.strip()
            df['internal_credito_id'] = df['credito_id_str'].map(ext_to_internal_id)

            # Filtramos transferencias que no encuentren su crédito para evitar errores de Foreign Key
            unmapped = df['internal_credito_id'].isna()
            if unmapped.any():
                print(f"⚠️ Atención: Hay {unmapped.sum()} transferencias cuyos créditos (ID externo) no existen en la BD. Serán omitidas.")
                df = df[~unmapped]

            CHUNK_SIZE = 5000
            
            for start_idx in range(0, len(df), CHUNK_SIZE):
                chunk_df = df.iloc[start_idx:start_idx + CHUNK_SIZE]
                chunk_dicts = chunk_df.to_dict('records')
                
                chunk_mappings = []
                for row in chunk_dicts:
                    mapping = {
                        "cbu": str(row['CBU']),
                        "monto": float(row['monto']),
                        "cuit": str(row['CUIT']),
                        "credito_id": int(row['internal_credito_id']),
                        "razon_social": str(row['razon_social'])
                    }
                    chunk_mappings.append(mapping)
                
                if chunk_mappings:
                    db.bulk_insert_mappings(Transferencia, chunk_mappings)
                    db.commit()
            
            print(f"✅ Se importaron {len(df)} transferencias exitosamente.")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error durante la importación de transferencias: {e}")
            raise e
