import os
from sqlalchemy import create_engine, text
from src.database import engine

with engine.connect() as conn:
    res = conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name = 'cuentas_comitentes' AND column_name = 'id_externo';")).fetchall()
    print('cuentas_comitentes.id_externo type:', res)
    res2 = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'movimientos_deuda';")).fetchall()
    print('movimientos_deuda columns:', [r[0] for r in res2])
    res3 = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'posiciones_iibb';")).fetchall()
    print('posiciones_iibb columns:', [r[0] for r in res3])
