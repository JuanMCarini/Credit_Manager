from sqlalchemy import text
from src.database.connection import engine

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE clientes ADD COLUMN sujeto_obligado BOOLEAN DEFAULT FALSE"))
            conn.commit()
            print("Column 'sujeto_obligado' added successfully to PostgreSQL.")
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    migrate()
