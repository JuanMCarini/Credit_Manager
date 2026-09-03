import sqlalchemy
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import engine

def main():
    try:
        with engine.connect() as conn:
            # PostgreSQL type is tiporolenum (lowercase) by default if not quoted in alembic, let's see.
            # Usually it's created as tiporolenum
            res = conn.execute(sqlalchemy.text("SELECT typname FROM pg_type WHERE typtype = 'e';")).fetchall()
            print("Enums:", res)
            
            # For the ones that exist, let's alter type
            for e in ['Gerente', 'Operador de Inversiones', 'Responsable de Finanzas']:
                try:
                    conn.execute(sqlalchemy.text(f"ALTER TYPE tiporolenum ADD VALUE '{e}';"))
                    conn.commit()
                    print(f"Agregado {e} a tiporolenum")
                except Exception as ex:
                    print(f"Error {e} tiporolenum:", ex)
                    try:
                        conn.execute(sqlalchemy.text(f"ALTER TYPE \"TipoRolEnum\" ADD VALUE '{e}';"))
                        conn.commit()
                        print(f"Agregado {e} a TipoRolEnum")
                    except Exception as ex2:
                        print(f"Error {e} TipoRolEnum:", ex2)
                        
    except Exception as e:
        print("General error:", e)

if __name__ == "__main__":
    main()
