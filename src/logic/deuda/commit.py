from datetime import date
from sqlalchemy import func

from src.database.models.deuda import Inversor, CuentaComitente, TitularidadCuentaComitente, Serie
from src.database.models.deuda.movimientos import MovimientoDeuda, TipoMovimiento, TitularidadMovimientoDeuda


def new_serie(db, nombre: str, fecha: date, tna: float, plazo: int):
    serie = db.query(Serie).filter(Serie.name == nombre).first()
    if not serie:
        serie = Serie(
            name=nombre,
            fecha_suscripcion=fecha,
            tna=tna,
            plazo=plazo,
        )
        db.add(serie)
        db.flush()  # Para obtener el serie.id
    return serie

def new_cta_cte(db, id_externo, row):
    if id_externo is not None:
        try:
            id_externo = str(id_externo)
        except (ValueError, TypeError):
            id_externo = str(id_externo).strip()
    cuenta = db.query(CuentaComitente).filter(CuentaComitente.id_externo == id_externo).first()
    if not cuenta:
        cuenta = CuentaComitente(
            id_externo=id_externo,
            conjunta=row["Conjunta"]
        )
        db.add(cuenta)
        db.flush() # Para obtener cuenta.id
    return cuenta

def new_inversor(db, cuit, rs, direccion):
    # Buscar o crear Inversor
    cuit = str(cuit).strip().replace("-", "")
    if cuit.endswith(".0"):
        cuit = cuit[:-2]
        
    inversor = db.query(Inversor).filter(Inversor.cuit == cuit).first()
    if not inversor:
        inversor = Inversor(
            cuit=cuit,
            razon_social=rs,
            domicilio_legal=direccion
        )
        db.add(inversor)
        db.flush() # Para obtener inversor.id

    return inversor

def new_titular(db, id_cuenta, id_inversor):
    titularidad_cta = db.query(TitularidadCuentaComitente).filter(
            TitularidadCuentaComitente.id_cuenta_comitente == id_cuenta,
            TitularidadCuentaComitente.id_inversor == id_inversor
        ).first()

    if not titularidad_cta:
        # Lo agregamos siempre al final (ignorando el orden sugerido)
        max_orden = db.query(func.max(TitularidadCuentaComitente.orden)).filter(
            TitularidadCuentaComitente.id_cuenta_comitente == id_cuenta
        ).scalar() or 0
        nuevo_orden = max_orden + 1

        titularidad_cta = TitularidadCuentaComitente(
            id_cuenta_comitente=id_cuenta,
            id_inversor=id_inversor,
            orden=nuevo_orden
        )
        db.add(titularidad_cta)
        db.flush()
    return titularidad_cta

def new_movimiento(db, id_cuenta, id_serie, fecha, monto, tipo, inversores):
    # Crear el MovimientoDeuda
    movimiento = MovimientoDeuda(
        id_cuenta_comitente=id_cuenta,
        id_serie=id_serie,
        fecha=fecha,
        monto=monto,
        tipo_movimiento=tipo
    )
    db.add(movimiento)
    db.flush() # Para obtener movimiento.id

    # Asociar los titulares al Movimiento
    for inversor in inversores:
        titularidad_mov = TitularidadMovimientoDeuda(
            id_movimiento_deuda=movimiento.id,
            id_inversor=inversor.id
        )
        db.add(titularidad_mov)

    return movimiento