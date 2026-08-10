from sqlalchemy import text
from src.database import engine

def main():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM conceptos WHERE name IN ('Pago a Proveedores', 'Transferencia Recibida', 'Transferencia Emitida')"))
        conn.commit()
        print("Conceptos eliminados.")

if __name__ == "__main__":
    main()
