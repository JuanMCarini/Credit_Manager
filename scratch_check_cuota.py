from src.database.connection import engine
import pandas as pd

with engine.connect() as conn:
    df_cobr = pd.read_sql("SELECT * FROM cobranzas WHERE cuota_id = 7267", conn)
    print("--- COBRANZAS CUOTA 7267 ---")
    print(df_cobr.to_string())
