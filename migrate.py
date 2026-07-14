from src.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE tasas_y_comisiones ADD COLUMN porcentaje_sellado NUMERIC(15, 6) DEFAULT 0.0;"))
    conn.commit()
print("DB Updated!")
