from src.database.connection import engine
import pandas as pd

with engine.connect() as conn:
    df_procesos = pd.read_sql("SELECT * FROM procesos ORDER BY id DESC LIMIT 5", conn)
    print("--- ULTIMOS PROCESOS ---")
    print(df_procesos[['id', 'tipo', 'estado', 'fecha_ejecucion']].to_string())
