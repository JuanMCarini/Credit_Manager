from src.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE clientes ADD COLUMN cuenta_bancaria VARCHAR(50);"))
    conn.execute(text("ALTER TABLE clientes ADD COLUMN banco VARCHAR(100);"))
    conn.commit()
print("DB Updated!")
