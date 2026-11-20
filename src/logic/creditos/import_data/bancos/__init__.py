from typing import Callable
from sqlalchemy.orm import Session, joinedload

from src.database.models.finance.bancos import (
    Concepto,
    Cuenta,
    RolSistemaConcepto,
    find_socio_for_banco,
)
from src.database.models.socios import Relacion


def extract_clean_detalle(descripcion: str | None) -> str:
    """Extrae el detalle limpio de una descripción bancaria removiendo el sufijo de referencia."""
    if not descripcion:
        return ""
    text = str(descripcion).strip()
    if " - Ref: " in text:
        text = text.split(" - Ref: ")[0].strip()
    return text.strip()


def load_bank_concepto_resolver(
    session: Session, cuenta_id: int
) -> Callable[[str, float, str | None], int]:
    """
    Carga las relaciones de conceptos configuradas para el banco de la cuenta
    y retorna una función para resolver el concepto_id de cada movimiento.
    """
    cuenta = (
        session.query(Cuenta)
        .options(joinedload(Cuenta.banco))
        .filter(Cuenta.id == cuenta_id)
        .first()
    )

    socio = None
    if cuenta and cuenta.banco:
        socio = find_socio_for_banco(session, cuenta.banco)

    mapa_relaciones = (
        Relacion.get_external_mapping_cache(socio.id, "conceptos", session)
        if socio
        else {}
    )
    mapa_relaciones_norm = {
        str(k).strip().lower(): int(v)
        for k, v in mapa_relaciones.items()
        if str(k).strip()
    }

    conceptos_db = session.query(Concepto).all()
    mapa_conceptos_lower = {
        (c.name or "").strip().lower(): c.id for c in conceptos_db
    }
    mapa_conceptos_rol = {
        c.rol_sistema: c.id for c in conceptos_db if c.rol_sistema
    }
    valid_concepto_ids = {c.id for c in conceptos_db}

    id_ingreso_nc = (
        mapa_conceptos_rol.get(RolSistemaConcepto.INGRESO_NO_CLASIFICADO.value)
        or mapa_conceptos_lower.get("ingreso no clasificado")
    )
    id_egreso_nc = (
        mapa_conceptos_rol.get(RolSistemaConcepto.EGRESO_NO_CLASIFICADO.value)
        or mapa_conceptos_lower.get("egreso no clasificado")
    )

    if not id_ingreso_nc or not id_egreso_nc:
        raise ValueError("Faltan los conceptos de 'NO CLASIFICADO' en la base de datos.")

    def resolve_concepto_id(
        transaccion: str, importe: float, desc: str | None = None
    ) -> int:
        candidates: list[str] = []
        if desc:
            desc_clean = str(desc).strip()
            if desc_clean:
                candidates.append(desc_clean)
            clean_detalle = extract_clean_detalle(desc_clean)
            if clean_detalle and clean_detalle not in candidates:
                candidates.append(clean_detalle)
        if transaccion:
            trans_clean = str(transaccion).strip()
            if trans_clean and trans_clean not in candidates:
                candidates.append(trans_clean)

        for candidate in candidates:
            concepto_id = mapa_relaciones.get(candidate)
            if concepto_id is None:
                concepto_id = mapa_relaciones_norm.get(candidate.lower())
            if concepto_id in valid_concepto_ids:
                return int(concepto_id)

        if importe < 0:
            return id_egreso_nc
        return id_ingreso_nc

    return resolve_concepto_id
