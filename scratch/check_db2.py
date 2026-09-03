import os
from sqlalchemy import create_engine, text
from src.database import engine

with engine.connect() as conn:
    res = conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name = 'movimientos_deuda' AND column_name = 'monto';")).fetchall()
    print('movimientos_deuda.monto type:', res)
    
    # Check if id_serie_destino exists
    res_cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'movimientos_deuda' AND column_name = 'id_serie_destino';")).fetchall()
    print('id_serie_destino exists:', bool(res_cols))

    try:
        res_enum = conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'tipomovimiento'::regtype;")).fetchall()
        print('tipomovimiento enum values:', [r[0] for r in res_enum])
    except Exception as e:
        print('tipomovimiento enum check error:', e)
