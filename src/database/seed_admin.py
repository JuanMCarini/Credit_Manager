from sqlalchemy.orm import Session
from .connection import SessionLocal, engine
from src.database.models import auth
from src.api.dependencies.auth import get_password_hash

def seed_admin():
    auth.Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        # Crear roles si no existen
        for rol_enum in auth.TipoRolEnum:
            if not db.query(auth.Rol).filter_by(nombre=rol_enum.value).first():
                db.add(auth.Rol(nombre=rol_enum.value))
        db.commit()

        admin_role = db.query(auth.Rol).filter_by(nombre=auth.TipoRolEnum.ADMINISTRADOR.value).first()
        
        # Crear usuario maestro si no existe
        if not db.query(auth.Usuario).filter_by(email="admin@creditmanager.com").first():
            admin_user = auth.Usuario(
                email="admin@creditmanager.com",
                hashed_password=get_password_hash("AdminPass123!"),
                nombre_completo="Usuario Maestro",
                rol_id=admin_role.id if admin_role else None
            )
            db.add(admin_user)
            db.commit()
            print("Usuario Maestro creado exitosamente.")
        else:
            print("El usuario maestro ya existe.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
