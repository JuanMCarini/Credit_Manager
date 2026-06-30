from src.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    # First check if the type exists and if we can alter it
    try:
        conn.execute(text("ALTER TYPE tipocobranzaenum ADD VALUE IF NOT EXISTS 'AJUSTE'"))
        conn.commit()
        print("Enum updated successfully")
    except Exception as e:
        print("Failed to update Enum:", str(e))
