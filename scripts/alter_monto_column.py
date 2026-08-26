import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database import SessionLocal
from sqlalchemy import create_engine, text

def alter_table():
    engine = create_engine("postgresql+pg8000://usuario_db:password_seguro@localhost:5434/credit_manager_db")
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE movimientos_deuda ALTER COLUMN monto TYPE NUMERIC(18, 2);"))
            print("Successfully altered column 'monto' to NUMERIC(18, 2)")
        except Exception as e:
            print(f"Error altering table: {e}")

if __name__ == "__main__":
    alter_table()
