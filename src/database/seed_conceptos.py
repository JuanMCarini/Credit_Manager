from sqlalchemy.orm import Session
from src.database.models.finance.bancos import Concepto, CategoriaMovimiento

def seed_conceptos(db: Session) -> None:
    print("Iniciando seeder de conceptos...")
    conceptos_base = [
        # --- Saldos Iniciales ---
        {
            "name": "Saldo Inicial",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Saldo Inicial de Cuenta"
        },
        {
            "name": "Saldo Inicial FCI",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Saldo Inicial FCI"
        },
        {
            "name": "Saldo Inicial Plazo Fijo",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Saldo Inicial Plazo Fijo"
        },

        # --- Cobranzas y Operaciones ---
        {
            "name": "Cobranza de Cuotas",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Cobranza de cuotas de créditos"
        },
        {
            "name": "Venta Cartera",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Venta de Cartera"
        },
       
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
        {
            "name": "Intereses Ganados",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Intereses ganados por inversiones"
        },

        # --- Impuestos, Comisiones y Gastos ---
        {
            "name": "Comisión Colocación",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Comisiones por colocación"
        },
        {
            "name": "Comisión transferencia HB",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Comisión transferencia HB"
        },
        {
            "name": "Comisión por Pago a Prov Ctas Otros Bcos",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Comisión por Pago a Prov Ctas Otros Bcos"
        },
        {
            "name": "Mantenimiento de Cuenta",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Mantenimiento de Cuenta"
        },
        {
            "name": "Impuesto Crédito",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Impuesto Crédito"
        },
        {
            "name": "Impuesto Débito",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Impuesto Débito"
        },
        {
            "name": "IVA Resp. Inscripto",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "IVA Resp. Inscripto"
        },
        {
            "name": "VEP ARCA",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "VEP de ARCA"
        },
        {
            "name": "Servicio de Cuenta",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Comisión por Servicio de Cuenta"
        },

        # --- No Clasificados ---
        {
            "name": "Ingreso NO CLASIFICADO",
            "tipo_movimiento": CategoriaMovimiento.INGRESO,
            "descripcion": "Ingreso no clasificado"
        },
        {
            "name": "EGRESO NO CLASIFICADO",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Egreso no clasificado"
        },

        # --- Colocación de Créditos
        {
            "name": "Colocación de Créditos",
            "tipo_movimiento": CategoriaMovimiento.EGRESO,
            "descripcion": "Pago capital por crédito vendido"
        }
    ]

    for c_data in conceptos_base:
        existing = db.query(Concepto).filter_by(name=c_data["name"]).first()
        if not existing:
            nuevo = Concepto(
                name=c_data["name"],
                tipo_movimiento=c_data["tipo_movimiento"],
                descripcion=c_data["descripcion"],
                is_system=True
            )
            db.add(nuevo)
        else:
            existing.tipo_movimiento = c_data["tipo_movimiento"]
            existing.descripcion = c_data["descripcion"]
            existing.is_system = True
    
    db.commit()
    print("Seeder de conceptos finalizado.")

if __name__ == "__main__":
    from src.database import SessionLocal
    db = SessionLocal()
    try:
        seed_conceptos(db)
    finally:
        db.close()
