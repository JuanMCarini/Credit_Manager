import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.connection import engine

def migrate():
    with engine.begin() as conn:
        try:
            # Check if column exists first to be idempotent
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comprobantes' and column_name='concepto_id';
            """))
            if result.fetchone() is None:
                print("Adding concepto_id to comprobantes table...")
                conn.execute(text("ALTER TABLE comprobantes ADD COLUMN concepto_id INTEGER REFERENCES conceptos(id) ON DELETE SET NULL;"))
                print("Migration complete.")
            else:
                print("Column concepto_id already exists.")
        except Exception as e:
            print(f"Error migrating: {e}")

if __name__ == "__main__":
    migrate()
