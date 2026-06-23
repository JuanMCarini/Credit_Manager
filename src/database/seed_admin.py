from sqlalchemy.orm import Session
from .connection import SessionLocal, engine
from src.database.models import auth
from src.api.dependencies.auth import get_password_hash

def seed_admin(db: Session = None):
    auth.Base.metadata.create_all(bind=engine)
    
    session = db if db else SessionLocal()
    
    try:
        # Crear roles si no existen
        for rol_enum in auth.TipoRolEnum:
            if not session.query(auth.Rol).filter_by(nombre=rol_enum.value).first():
                session.add(auth.Rol(nombre=rol_enum.value))
        session.commit()

        admin_role = session.query(auth.Rol).filter_by(nombre=auth.TipoRolEnum.ADMINISTRADOR.value).first()
        
        # Crear usuario maestro si no existe
        if not session.query(auth.Usuario).filter_by(email="admin@creditmanager.com").first():
            admin_user = auth.Usuario(
                email="admin@creditmanager.com",
                hashed_password=get_password_hash("123456"),
                nombre_completo="Usuario Maestro",
                rol_id=admin_role.id if admin_role else None
            )
            session.add(admin_user)
            session.commit()
            print("✅ Usuario Maestro creado exitosamente.")
        else:
            print("✅ El usuario maestro ya existe.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        session.rollback()
    finally:
        if not db:
            session.close()

if __name__ == "__main__":
    seed_admin()
