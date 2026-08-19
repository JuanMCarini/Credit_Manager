from src.database.connection import SessionLocal
from src.database.models.finance.bancos import Banco
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def seed_bancos():
    db = SessionLocal()
    try:
        bancos_existentes = {b.nombre_banco for b in db.query(Banco).all()}
        nuevos = 0
        for nombre in BANCOS_ARGENTINA:
            if nombre not in bancos_existentes:
                nuevo_banco = Banco(nombre_banco=nombre)
                db.add(nuevo_banco)
                nuevos += 1
        
        db.commit()
        logger.info(f"Se insertaron {nuevos} bancos nuevos.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al sembrar bancos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_bancos()
