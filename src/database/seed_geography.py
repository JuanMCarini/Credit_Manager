"""
Module: seed_geography.py
Description: Script to populate the 'provincias' table with legacy IDs.
Author: Juan Martín Carini
"""

from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import Provincia


def seed_provincias(db: Session) -> None:
    """
    Populates the 'provincias' table using hardcoded IDs from the legacy system.
    Filters out duplicate entries, keeping only the first declared ID.
    """
    provincias_data = [
        {"id": 1, "nombre": "BUENOS AIRES"},
        {"id": 2, "nombre": "CATAMARCA"},
        {"id": 3, "nombre": "CORDOBA"},
        {"id": 4, "nombre": "CAPITAL FEDERAL"},
        {"id": 5, "nombre": "CHACO"},
        {"id": 6, "nombre": "CORRIENTES"},
        {"id": 7, "nombre": "CHUBUT"},
        {"id": 8, "nombre": "ENTRE RIOS"},
        {"id": 9, "nombre": "FORMOSA"},
        {"id": 10, "nombre": "JUJUY"},
        {"id": 11, "nombre": "LA PAMPA"},
        {"id": 12, "nombre": "LA RIOJA"},
        {"id": 13, "nombre": "MISIONES"},
        {"id": 14, "nombre": "MENDOZA"},
        {"id": 15, "nombre": "NEUQUEN"},
        {"id": 16, "nombre": "RIO NEGRO"},
        {"id": 18, "nombre": "SALTA"},
        {"id": 19, "nombre": "SANTA CRUZ"},
        {"id": 20, "nombre": "SANTIAGO DEL ESTERO"},
        {"id": 21, "nombre": "SANTA FE"},
        {"id": 22, "nombre": "SAN JUAN"},
        {"id": 23, "nombre": "SAN LUIS"},
        {"id": 24, "nombre": "TIERRA DEL FUEGO"},
        {"id": 25, "nombre": "TUCUMAN"},
    ]

    registros_insertados = 0

    for data in provincias_data:
        # Check if the ID already exists to prevent IntegrityError
        provincia_existente = db.query(Provincia).filter_by(id=data["id"]).first()

        if not provincia_existente:
            nueva_provincia = Provincia(id=data["id"], nombre=data["nombre"])
            db.add(nueva_provincia)
            registros_insertados += 1

    db.commit()
    print(f"✅ Se insertaron {registros_insertados} provincias correctamente.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_provincias(db)
    except Exception as e:
        db.rollback()
        print(f"❌ Error al poblar provincias: {e}")
    finally:
        db.close()
