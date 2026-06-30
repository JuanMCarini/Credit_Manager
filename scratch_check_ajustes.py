from src.database.connection import engine
import pandas as pd

with engine.connect() as conn:
    df_cobr = pd.read_sql("SELECT * FROM cobranzas WHERE proceso_id = 22 AND tipo_cobranza = 'AJUSTE'", conn)
    print("--- AJUSTES DEL PROCESO 22 ---")
    print(df_cobr.to_string())
