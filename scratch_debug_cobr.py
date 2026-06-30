from src.database.connection import engine
import pandas as pd

# Load cuota data
with engine.connect() as conn:
    df_cuota = pd.read_sql("SELECT * FROM cuotas WHERE credito_id = 594 AND nro_cuota = 4", conn)
    cuota_id = int(df_cuota['id'].iloc[0])
    
    print("--- CUOTA ---")
    print(df_cuota[['id', 'capital', 'interes', 'iva', 'estado']].to_string())
    print("\n--- COBRANZAS ---")
    df_cobr = pd.read_sql(f"SELECT * FROM cobranzas WHERE cuota_id = {cuota_id}", conn)
    print(df_cobr[['id', 'proceso_id', 'tipo_cobranza', 'capital', 'interes', 'iva', 'fecha']].to_string())
