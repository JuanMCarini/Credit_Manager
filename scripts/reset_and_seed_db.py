"""
Script: reset_and_seed_db.py
Description: Wipes the database clean (drops all tables) and seeds it from scratch
             with initial system data and company settings from .env (CREDISE S.A.).
"""

import sys
import os
from sqlalchemy import text

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import SessionLocal, engine, Base
import src.database.models  # Ensures all models and enums are registered
from src.database.models import SocioComercial, Rol, Usuario, TipoRolEnum
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
        conn.execute(text("GRANT ALL ON SCHEMA public TO usuario_db;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    print("   ✅ Esquema public reseteado a cero.")

    print("2. Creando todas las tablas según los modelos actuales...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Tablas y tipos ENUM creados exitosamente.")

    print("3. Ejecutando seeders del sistema...")
    # A. Roles y usuario admin
    seed_admin()
    print("   ✅ Roles y Usuario Maestro inicializados.")

    db = SessionLocal()
    try:
        # B. Restaurar usuario de la empresa (Ariel Tejada)
        gerente_role = db.query(Rol).filter_by(nombre="GERENTE").first()
        admin_role = db.query(Rol).filter_by(nombre=TipoRolEnum.ADMINISTRADOR.value).first()
        rol_ariel = gerente_role or admin_role

        user_ariel = db.query(Usuario).filter_by(email="arieltejada@credisesa.com.ar").first()
        if not user_ariel:
            user_ariel = Usuario(
                email="arieltejada@credisesa.com.ar",
                hashed_password="$2b$12$uV0iMhU2eCQACA1OQ9sUPekT94N9AZBfK/XISHJ7gEjsdgFRPNMly",
                nombre_completo="Jose Ariel Tejada",
                rol_id=rol_ariel.id if rol_ariel else None,
                is_active=True,
            )
            db.add(user_ariel)
            db.commit()
            print("   ✅ Usuario 'Jose Ariel Tejada' (arieltejada@credisesa.com.ar) creado.")

        # C. Crear empresa principal con los datos del .env
        razon_social = COMPANY_DATA.razon_social or "CREDISE S.A."
        cuit = COMPANY_DATA.cuit or "30717174220"
        domicilio = COMPANY_DATA.domicilio or "19 de Mayo 486, Bahía Blanca, Buenos Aires"
        email = COMPANY_DATA.email_contacto or "administracion@credisesa.com.ar"
        telefono = COMPANY_DATA.telefono or ""
        bank_account = COMPANY_DATA.bank_account or "CC-$ 10176607"
        bank_name = COMPANY_DATA.bank_name or "Banco Bica S.A."
        cbu = COMPANY_DATA.cbu or "4260004000100101766075"
        dia_corte = COMPANY_DATA.dia_corte or 28

        socio_existente = db.query(SocioComercial).filter(
            (SocioComercial.cuit == cuit) | (SocioComercial.razon_social == razon_social)
        ).first()

        if not socio_existente:
            nuevo_socio = SocioComercial.create_socio(
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

        # D. Provincias
        seed_provincias(db)

        # E. Conceptos
        seed_conceptos(db)

        # F. Módulos
        seed_modulos(db)

    finally:
        db.close()

    # G. Bancos
    seed_bancos()

    print("\n🎉 Base de datos reseteada e inicializada exitosamente.")


if __name__ == "__main__":
    reset_database()
