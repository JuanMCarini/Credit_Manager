from sqlalchemy.orm import Session
from src.database.models.system import ModuloSistema

DEFAULT_MODULOS = [
    {"codigo": "creditos", "nombre": "Cartera de Créditos", "activo": True},
    {"codigo": "cheques", "nombre": "Cartera de Cheques", "activo": True},
    {"codigo": "inversores", "nombre": "Inversores", "activo": True},
    {"codigo": "finanzas", "nombre": "Finanzas", "activo": True},
]

def seed_modulos(db: Session):
    """
    Verifica que los 4 módulos principales existan en la base de datos.
    Si alguno no existe, lo inicializa como activo por defecto.
    """
    try:
        modulos_existentes = {m.codigo: m for m in db.query(ModuloSistema).all()}
        nuevos = []
        for mod in DEFAULT_MODULOS:
            if mod["codigo"] not in modulos_existentes:
                nuevos.append(ModuloSistema(
                    codigo=mod["codigo"],
                    nombre=mod["nombre"],
                    activo=mod["activo"]
                ))
        if nuevos:
            db.add_all(nuevos)
            db.commit()
            print(f"✅ Se inicializaron {len(nuevos)} módulos del sistema.")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error al inicializar módulos del sistema: {e}")
