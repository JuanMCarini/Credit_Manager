import sys
import os
from sqlalchemy import text

# Agregamos la ruta principal para poder importar 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import Base, engine, SessionLocal, seed_admin, seed_provincias, seed_conceptos
from src.api.main import init_main_company
from src.config import DATABASE_SETTINGS

def reset_database():
    print(f"ATENCIÓN: Conectado a la base de datos: {DATABASE_SETTINGS.name}")
    print(f"Host: {DATABASE_SETTINGS.host}, Puerto: {DATABASE_SETTINGS.port}")
    
    # Confirmación de seguridad
    if DATABASE_SETTINGS.name != "credit_manager_db":
        print("ERROR: La base de datos configurada no es 'credit_manager_db'. Abortando por seguridad.")
        return

    print("Borrando tablas correspondientes a Fondosur...")
    # drop_all solo borra las tablas definidas en los modelos de SQLAlchemy, no toca otras bases de datos.
    Base.metadata.drop_all(bind=engine)
    
    print("Creando tablas nuevamente...")
    Base.metadata.create_all(bind=engine)
    
    print("Inicializando la empresa principal...")
    init_main_company()
    
    print("Cargando datos semilla (admin, provincias, conceptos)...")
    seed_admin()
    with SessionLocal() as db:
        seed_provincias(db)
        seed_conceptos(db)
        db.commit()
        
    print("¡Base de datos reseteada exitosamente!")

if __name__ == "__main__":
    reset_database()
