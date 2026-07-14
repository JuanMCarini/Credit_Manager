from src.database.connection import engine
from sqlalchemy import text

def add_compliance_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE clientes ADD COLUMN pep BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE clientes ADD COLUMN repet BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Columns 'pep' and 'repet' added successfully.")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    add_compliance_columns()
