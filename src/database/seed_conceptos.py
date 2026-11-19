from sqlalchemy import func
from sqlalchemy.orm import Session
from src.database.models.finance.bancos import Concepto, CategoriaMovimiento

def seed_conceptos(db: Session) -> None:
    print("Iniciando seeder de conceptos...")
    conceptos_base = [
        # --- Inversiones ---
        {
            "name": "Suscripción FCI",
            "tipo_movimiento": CategoriaMovimiento.SUSCRIPCION_FCI,
            "descripcion": "Suscripción de FCI"
        },
        {
            "name": "Rescate FCI",
            "tipo_movimiento": CategoriaMovimiento.RESCATE_FCI,
            "descripcion": "Rescate de FCI"
        },
        {
            "name": "Constitución Plazo Fijo",
            "tipo_movimiento": CategoriaMovimiento.PLAZO_FIJO_INGRESOS,
            "descripcion": "Constitución de Plazo Fijo"
        },
        {
            "name": "Vencimiento Plazo Fijo",
            "tipo_movimiento": CategoriaMovimiento.PLAZO_FIJO_EGRESOS,
            "descripcion": "Vencimiento de Plazo Fijo"
        },

        # --- No Clasificados ---
        {
            "name": "INGRESO NO CLASIFICADO",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Ingreso no clasificado"
        },
        {
            "name": "EGRESO NO CLASIFICADO",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Egreso no clasificado"
        },
    ]

    try:
        for c_data in conceptos_base:
            existing = (
                db.query(Concepto)
                .filter(func.lower(Concepto.name) == c_data["name"].lower())
                .first()
            )
            if not existing:
                nuevo = Concepto(
                    name=c_data["name"],
                    tipo_movimiento=c_data["tipo_movimiento"],
                    descripcion=c_data["descripcion"],
                    is_system=True
                )
                db.add(nuevo)
            else:
                existing.name = c_data["name"]
                existing.tipo_movimiento = c_data["tipo_movimiento"]
                existing.descripcion = c_data["descripcion"]
                existing.is_system = True

        db.commit()
        print("Seeder de conceptos finalizado.")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error en seeder de conceptos: {e}")

if __name__ == "__main__":
    from src.database import SessionLocal
    db = SessionLocal()
    try:
        seed_conceptos(db)
    finally:
        db.close()
