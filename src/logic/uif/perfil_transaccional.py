from IPython.core import display_functions
from pandas import Period, read_sql
from decimal import Decimal

from src.database import SessionLocal
from src.database.models import SocioComercial, TasaYComision, EstadoComisionEnum
from src.database.models.creditos.perfil_trans import PerfilTransaccional, ReglasPerfilTransaccional, TipoSueldo

def cuota_afectable(cuil: str, periodo: Period, socio: SocioComercial) -> float:
    """
    Calcula la cuota afectable máxima para un cliente y socio comercial dados, en un período específico.

    Toma en cuenta el ingreso (bruto o neto) del perfil transaccional del cliente, resta los conceptos indicados en las reglas del socio comercial (asignaciones, horas extras, etc.) y aplica el cupo correspondiente.

    Args:
        cuil (str): CUIL del cliente.
        periodo (Period): Período a evaluar (mes/año).
        socio (SocioComercial): Objeto del socio comercial con sus reglas asociadas.

    Returns:
        float: El valor máximo de la cuota afectable permitida, o 0.0 si no se encuentra información.
    """

    db = SessionLocal()

    try:
        regla = db.query(ReglasPerfilTransaccional).filter(ReglasPerfilTransaccional.id_socio_comercial == socio.id).first()
        perfil = db.query(PerfilTransaccional).filter(
            PerfilTransaccional.cuil_cliente == cuil,
            PerfilTransaccional.periodo == periodo.start_time.date()
        ).first()

        # Validación en caso de que no existan registros para no lanzar excepciones
        if not regla or not perfil:
            return 0.0, 0.0

        base = perfil.ingreso_neto if regla.sueldo_tipo == TipoSueldo.neto else perfil.ingreso_bruto

        base -= perfil.asignacion_familiar if regla.asignacion_familiar else Decimal('0')
        base -= perfil.horas_extras if regla.horas_extras else Decimal('0')
        base -= perfil.vacaciones if regla.vacaciones else Decimal('0')
        base -= perfil.otros if regla.otros else Decimal('0')

        if regla.descuentos_voluntarios:
            base -= perfil.descuentos_voluntarios
            cupo = base * regla.cupo
        else:
            cupo = base * regla.cupo
            cupo -= perfil.descuentos_voluntarios

        return float(base), float(cupo)
    
    finally:
        # Se asegura de cerrar la conexión incluso si ocurre un error
        db.close()


def capital_neto_maximo(cuil: str, periodo: Period, socio: SocioComercial) -> float:
    _, cupo = cuota_afectable(cuil, periodo, socio)

    db = SessionLocal()
    try:
        tasas = db.query(TasaYComision.id, TasaYComision.plazo, TasaYComision.tna_c_iva, TasaYComision.gasto_1_porcentaje , TasaYComision.gasto_2_porcentaje, TasaYComision.porcentaje_sellado).filter(
            TasaYComision.socio_originador_id == socio.id,
            TasaYComision.estado == EstadoComisionEnum.ACTIVA
        )
        df = read_sql(tasas.statement, db.get_bind())
        df["tem"] = df["tna_c_iva"] * 30 / 365
        # Cuota = Capital_Bruto * factor_cuota
        df["factor_cuota"] = df["tem"] / (1 - (1 + df["tem"]) ** (-df["plazo"]))
        
        # Capital Bruto Max = Cupo / factor_cuota
        df["cap_bruto_max"] = cupo / df["factor_cuota"]
        
        # Capital Neto Max = Capital Bruto Max * (1 - gastos)
        gastos = df["porcentaje_sellado"] + df["gasto_1_porcentaje"] + df["gasto_2_porcentaje"]
        df["cap_neto_max"] = df["cap_bruto_max"] * (1 - gastos)
        
        df.sort_values(by=["plazo"], inplace=True)

        regla = db.query(ReglasPerfilTransaccional).filter(ReglasPerfilTransaccional.id_socio_comercial == socio.id).first()
        df = df[(df["cap_neto_max"] >= regla.cap_min) & (df["cap_neto_max"] <= regla.cap_max)]

    finally:
        db.close()

    return df[["id", "plazo", "tna_c_iva", "cap_neto_max"]]