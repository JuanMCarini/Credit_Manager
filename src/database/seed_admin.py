import logging
import os
import secrets
from sqlalchemy.orm import Session
from .connection import SessionLocal, engine
from src.config import API_SETTINGS
from src.database.models import auth
from src.api.dependencies.auth import get_password_hash

logger = logging.getLogger(__name__)


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
        
        admin_email = (os.getenv("INITIAL_ADMIN_EMAIL") or "admin@creditmanager.com").strip()
        initial_password = (os.getenv("INITIAL_ADMIN_PASSWORD") or "").strip()
        current_env = (os.getenv("ENV") or API_SETTINGS.env or "development").strip().lower()

        # Crear usuario maestro si no existe
        if not session.query(auth.Usuario).filter_by(email=admin_email).first():
            generated_random = False
            if initial_password:
                if len(initial_password) < 12:
                    msg = (
                        "⚠️ INITIAL_ADMIN_PASSWORD debe tener al menos 12 caracteres. "
                        "Se omite la creación automática del usuario administrador."
                    )
                    logger.warning(msg)
                    print(msg)
                    return
                password_to_use = initial_password
            elif current_env == "production":
                msg = (
                    "⚠️ [PRODUCCIÓN] INITIAL_ADMIN_PASSWORD no está definida. "
                    "Se omite la creación automática del usuario administrador por seguridad."
                )
                logger.warning(msg)
                print(msg)
                return
            else:
                password_to_use = secrets.token_urlsafe(16)
                generated_random = True

            admin_user = auth.Usuario(
                email=admin_email,
                hashed_password=get_password_hash(password_to_use),
                nombre_completo="Usuario Maestro",
                rol_id=admin_role.id if admin_role else None
            )
            session.add(admin_user)
            session.commit()
            if generated_random:
                print(
                    f"✅ Usuario Maestro ({admin_email}) creado en entorno '{current_env}'. "
                    f"Contraseña temporal generada (guardar ahora, no se volverá a mostrar): {password_to_use}"
                )
            else:
                print(f"✅ Usuario Maestro ({admin_email}) creado exitosamente.")
        else:
            print(f"✅ El usuario maestro ({admin_email}) ya existe.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        session.rollback()
    finally:
        if not db:
            session.close()

if __name__ == "__main__":
    seed_admin()
