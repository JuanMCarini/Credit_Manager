import sys
sys.path.append('.')
from src.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE repet_audit_logs ADD COLUMN cuil_cliente VARCHAR(11) REFERENCES clientes(cuil)"))
    print("Column added successfully.")
