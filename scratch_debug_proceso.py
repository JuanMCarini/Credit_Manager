from src.database.connection import engine
import pandas as pd

with engine.connect() as conn:
    df_proceso = pd.read_sql("SELECT * FROM procesos WHERE id = 21", conn)
    print("--- PROCESO 21 ---")
    print(df_proceso.to_string())
