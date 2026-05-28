"""
=============================================================================
Module: penalties.py
Description: Contains the PenaltyManager class responsible for originating
             and managing late fee debts independently from standard loans.
=============================================================================
"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.database.models import Credito, Cuota, EstadoCuota, TipoCredito
from src.utils.dates import normalize_date


class PenaltyManager:
    """
    =============================================================================
    Class: PenaltyManager
    Description: Handles the business logic for generating penalty credits
                 (late fees). Separates penalty origination from standard
                 collection and origination pipelines.
    =============================================================================
    """

    def __init__(self, db_session: Session | None = None):
        self.db = db_session or SessionLocal()
        self._own_session = db_session is None

    def __del__(self):
        """
        Safely closes the database session if it was created internally.
        """
        if hasattr(self, "_own_session") and self._own_session and hasattr(self, "db") and self.db:
            self.db.close()

    def generate_penalty_credit(
        self,
        credito_origen_id: int | list,
        monto_punitorio: float,
        fecha_emision: datetime | str | None = None,
        fecha_vencimiento: datetime | str | None = None,
        tasa_iva: float = 0.21,
        commit: bool = True,
    ) -> Credito:
        """
        =============================================================================
        Method: generate_penalty_credit
        Description: Originates a standalone PENALTY credit line to represent late fees.
                     Automatically fetches the client's CUIL from the original credit.
                     Bypasses standard amortization engines to prevent mathematical
                     errors, as the debt consists entirely of interest and taxes.
        Parameters:
            credito_origen_id (int): ID of the original credit that generated the delay.
            monto_punitorio (float): The gross penalty amount (interest + VAT).
            fecha_emision (datetime | str | None): Issue date for the penalty.
            fecha_vencimiento (datetime | str | None): Due date for the penalty.
            tasa_iva (float): Applicable tax rate.
        Returns:
            Credito: The instantiated penalty credit with its associated installment.
        Raises:
            ValueError: If the original credit ID does not exist in the database.
            RuntimeError: If the database transaction fails to commit.
        =============================================================================
        """
        vencimiento = normalize_date(fecha_vencimiento)
        emision = normalize_date(fecha_emision)

        id_externo = str(credito_origen_id)
        if type(credito_origen_id) is list:
            credito_origen_id = credito_origen_id[0]
        id_externo = f"PEN-{id_externo}"
        # 0. Retrieve the original credit to extract cliente_cuil safely
        original_credit = (
            self.db.query(Credito).filter(Credito.id == credito_origen_id).first()
        )
        if not original_credit:
            raise ValueError(
                f"Origin credit with ID {credito_origen_id} not found."
            )

        cliente_cuil = original_credit.cliente_cuil

        # 1. Instantiate the parent credit marked as PENALTY
        penalty_credit = Credito(
            tipo_credito=TipoCredito.PENALTY.value,
            cliente_cuil=cliente_cuil,
            id_externo=id_externo,
            capital=0.0,
            tna_c_iva=0.0,
            plazo=1,
            fecha_emision=emision,
            dia_vencimiento=vencimiento.day,
        )

        self.db.add(penalty_credit)
        self.db.flush()

        # 2. Generate the single penalty installment (Fixed VAT math)
        monto_bruto = round(monto_punitorio, 2)
        interes_neto = round(monto_bruto / (1 + tasa_iva), 2)
        monto_iva = round(monto_bruto - interes_neto, 2)

        penalty_cuota = Cuota(
            credito_id=penalty_credit.id,
            nro_cuota=1,
            fecha_vencimiento=vencimiento,
            capital=0.0,
            interes=interes_neto,
            iva=monto_iva,
            estado=EstadoCuota.CANCELADA,
        )
        self.credit = penalty_credit
        self.cuota = penalty_cuota
        self.db.add(penalty_cuota)

        try:
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return penalty_credit, penalty_cuota
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error generating PENALTY credit: {e}")
