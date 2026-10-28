"""
Script: reset_and_seed_db.py
Description: Wipes the database clean (drops all tables) and seeds it from scratch
             with initial system data and company settings from .env.
"""

import sys
import os
from sqlalchemy import text

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import SessionLocal, engine, Base
import src.database.models  # noqa: F401 - Ensures all models and enums are registered
from src.database.models import SocioComercial
from src.database.seed_admin import seed_admin
from src.database.seed_bancos import seed_bancos
from src.database.seed_geography import seed_provincias
from src.database.seed_conceptos import seed_conceptos
from src.database.seed_modulos import seed_modulos
from src.config import COMPANY_DATA


def reset_database():
    print("1. Limpiando la base de datos completamente (Drop Schema public CASCADE)...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    print("   ✅ Esquema public reseteado a cero.")

    print("2. Creando todas las tablas según los modelos actuales...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Tablas y tipos ENUM creados exitosamente.")

    print("3. Ejecutando seeders del sistema...")
    # A. Roles y usuario admin (admin@creditmanager.com / 123456)
    seed_admin()
    print("   ✅ Roles y Usuario Maestro inicializados.")

    db = SessionLocal()
    try:
        # B. Crear empresa principal con los datos del .env
        razon_social = COMPANY_DATA.razon_social
        cuit = COMPANY_DATA.cuit
        domicilio = COMPANY_DATA.domicilio
        email = COMPANY_DATA.email_contacto
        telefono = COMPANY_DATA.telefono
        bank_account = COMPANY_DATA.bank_account
        bank_name = COMPANY_DATA.bank_name
        cbu = COMPANY_DATA.cbu
        dia_corte = COMPANY_DATA.dia_corte or 28

        socio_existente = db.query(SocioComercial).filter(
            (SocioComercial.cuit == cuit) | (SocioComercial.razon_social == razon_social)
        ).first()

        if not socio_existente:
            SocioComercial.create_socio(
                razon_social=razon_social,
                cuit=cuit,
                db=db,
                domicilio_legal=domicilio,
                mail=email,
                telefono=telefono,
                cbu=cbu,
                nro_cuenta_bancaria=bank_account,
                nombre_banco=bank_name,
                dia_corte=dia_corte,
            )
            print(f"   ✅ Empresa principal '{razon_social}' (CUIT: {cuit}) creada como Socio Comercial principal.")
        else:
            print(f"   ℹ️ Empresa principal '{razon_social}' ya existe.")

        # C. Provincias
        seed_provincias(db)

        # D. Conceptos
        seed_conceptos(db)

        # E. Módulos
        seed_modulos(db)

    finally:
        db.close()

    # F. Bancos
    seed_bancos()

    print("\n🎉 Base de datos reseteada e inicializada exitosamente.")


if __name__ == "__main__":
    reset_database()
