import os
from sqlalchemy import create_engine, text
from src.database import engine

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE movimientos_deuda ADD COLUMN id_serie_destino INTEGER REFERENCES series(id);"))
        conn.commit()
        print("Column id_serie_destino added successfully.")
    except Exception as e:
        print("Error:", e)
