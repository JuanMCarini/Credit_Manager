from src.database.connection import SessionLocal
from src.database.models.finance.bancos import Banco, find_socio_for_banco
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PARSERS = {
    "Banco Santander": "santander",
    "Banco de La Pampa": "pampa",
    "Banco Bica": "bica",
}

BANCOS_ARGENTINA = [
    "Banco de la Nación Argentina",
    "Banco de la Provincia de Buenos Aires",
    "Banco Ciudad de Buenos Aires",
    "Banco Galicia",
    "Banco Santander",
    "Banco BBVA",
    "Banco Macro",
    "Banco Patagonia",
    "Industrial and Commercial Bank of China (ICBC)",
    "Banco Credicoop",
    "Banco Supervielle",
    "Banco Hipotecario",
    "Banco Comafi",
    "Banco de Córdoba",
    "Nuevo Banco de Santa Fe",
    "Banco de La Pampa",
    "Banco de Entre Ríos",
    "Banco de San Juan",
    "Banco de Santa Cruz",
    "Banco Bica",
    "Banco Coinag",
    "Banco de Corrientes",
    "Banco del Chubut",
    "Banco de Tierra del Fuego",
    "Banco de Formosa",
    "Nuevo Banco del Chaco",
    "Banco de Santiago del Estero",
    "Banco Industrial (BIND)",
    "Banco Mariva",
    "Banco Meridian",
    "Banco Piano",
    "Banco Roela",
    "Banco Sáenz",
    "Banco Julio",
    "Banco de Inversión y Comercio Exterior (BICE)",
    "Brubank",
    "Openbank",
    "Reba",
    "Wilobank",
]

def seed_bancos(db=None):
    session = db if db is not None else SessionLocal()
    try:
        bancos_existentes = {b.nombre_banco for b in session.query(Banco).all()}
        nuevos = 0
        for nombre in BANCOS_ARGENTINA:
            if nombre not in bancos_existentes:
                nuevo_banco = Banco(
                    nombre_banco=nombre,
                    parser_type=DEFAULT_PARSERS.get(nombre),
                )
                session.add(nuevo_banco)
                nuevos += 1

        session.flush()

        for banco in session.query(Banco).all():
            if banco.nombre_banco in DEFAULT_PARSERS and banco.parser_type is None:
                banco.parser_type = DEFAULT_PARSERS[banco.nombre_banco]

            if not banco.socio_id:
                find_socio_for_banco(session, banco)

        session.commit()
        logger.info(f"Se insertaron {nuevos} bancos nuevos.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error al sembrar bancos: {e}")
    finally:
        if db is None:
            session.close()

if __name__ == "__main__":
    seed_bancos()
