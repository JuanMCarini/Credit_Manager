"""
Module: origination.py
Description: Object-oriented loan origination pipeline.
"""

from datetime import date

from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import (
    Cliente,
    Credito,
    EstadoCredito,
    SocioComercial,
    TipoCredito,
    Transferencia,
)
from src.logic.creditos.amortization import AmortizationEngine


class LoanOriginator:
    """
    =============================================================================
    Class: LoanOriginator
    Description: Orchestrates the formal origination of new credits. Handles both
                 existing clients and simultaneous onboarding of new customers.
                 Ensures atomic transactions and automatic schedule generation.
    =============================================================================
    """

    def __init__(self, db_session: Session | None = None):
        self.db = db_session or SessionLocal()
        self.client: Cliente | None = None
        self.partner: SocioComercial | None = None
        self.credit: Credito | None = None

    def _validate_client(self, client_cuil: str) -> None:
        """
        =============================================================================
        Method: _validate_client
        Description: Ensures the client exists before processing a standard loan.
        =============================================================================
        """
        self.client = self.db.query(Cliente).filter_by(cuil=client_cuil).first()
        if not self.client:
            raise ValueError(
                f"Client with CUIL {client_cuil} not found. Register the client first."
            )

    def _get_partner_cutoff_day(self, partner_id: int | None) -> int:
        """
        =============================================================================
        Method: _get_partner_cutoff_day
        Description: Retrieves the partner's cutoff day for grace period calculation.
        =============================================================================
        """
        if partner_id:
            self.partner = self.db.query(SocioComercial).get(partner_id)
            if self.partner:
                return self.partner.dia_corte
        return 28

    def _generate_credit_and_schedule(
        self,
        capital: float,
        tna_c_iva: float,
        term: int,
        partner_id: int | None,
        issuance_date: date,
        due_day: int,
        cutoff_day: int,
        type: TipoCredito,
        comercializador_id: int | None = None,
        comision_id: int | None = None,
        id_externo: str | None = None,
    ) -> None:
        """
        =============================================================================
        Method: _generate_credit_and_schedule
        Description: Internal helper to instantiate the credit and its installments.
        =============================================================================
        """
        self.credit = Credito(
            cliente_cuil=self.client.cuil,
            socio_originador_id=partner_id,
            comercializador_id=comercializador_id,
            comision_id=comision_id,
            capital=capital,
            tna_c_iva=tna_c_iva,
            plazo=term,
            fecha_emision=issuance_date,
            estado=EstadoCredito.APROBADO,
            dia_vencimiento=due_day,
            tipo_credito=type,
            id_externo=id_externo,
        )

        self.db.add(self.credit)
        self.db.flush()  # Generate Credit ID for installments

        if type == TipoCredito.FRANCES:
            installments = AmortizationEngine.generate_french_schedule(
                credito_id=self.credit.id,
                capital=capital,
                tna_c_iva=tna_c_iva,
                plazo=term,
                fecha_emision=issuance_date,
                dia_vencimiento=due_day,
                dia_corte=cutoff_day,
            )
        else:
            raise ValueError(
                f"The credit type {type.value} is not configured yet."
            )

        self.db.add_all(installments)

    def originate(
        self,
        client_cuil: str,
        capital: float,
        tna_c_iva: float,
        term: int,
        partner_id: int | None = None,
        issuance_date: date | None = None,
        due_day: int = 28,
        type: TipoCredito = TipoCredito.FRANCES,
        comercializador_id: int | None = None,
        comision_id: int | None = None,
        id_externo: str | None = None,
        transferencias_data: list = None,
        commit: bool = True,
    ) -> Credito:
        """
        =============================================================================
        Method: originate
        Description: Originates a loan for an already existing client.
        =============================================================================
        """
        if issuance_date is None:
            issuance_date = date.today()

        try:
            self._validate_client(client_cuil)
            cutoff_day = self._get_partner_cutoff_day(partner_id)
            self._generate_credit_and_schedule(
                capital, tna_c_iva, term, partner_id, issuance_date, due_day, cutoff_day, type, comercializador_id, comision_id, id_externo
            )


            if getattr(self.credit, 'comision', None) and getattr(self.credit.comision, 'porcentaje_sellado', 0):
                porcentaje = float(self.credit.comision.porcentaje_sellado)
                if porcentaje > 0:
                    monto_sellado = float(self.credit.capital) * porcentaje
                    t_sellado = Transferencia(
                        credito_id=self.credit.id,
                        cbu=None,
                        monto=monto_sellado,
                        cuit="",
                        razon_social="Sellado"
                    )
                    self.db.add(t_sellado)

            if transferencias_data:
                for t_data in transferencias_data:
                    # Depending on if it's Pydantic model or dict
                    t_dict = t_data.dict() if hasattr(t_data, 'dict') else t_data
                    transferencia = Transferencia(
                        credito_id=self.credit.id,
                        cbu=t_dict['cbu'],
                        monto=t_dict['monto'],
                        cuit=t_dict['cuit'],
                        razon_social=t_dict['razon_social']
                    )
                    self.db.add(transferencia)

            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return self.credit

        except Exception as e:
            if commit:
                self.db.rollback()
            raise RuntimeError(f"Failed to originate credit: {e}")

    def originate_with_new_client(
        self,
        client_data: dict,
        capital: float,
        tna_c_iva: float,
        term: int,
        partner_id: int | None = None,
        issuance_date: date | None = None,
        due_day: int = 28,
        type: TipoCredito = TipoCredito.FRANCES,
        comision_id: int | None = None,
        id_externo: str | None = None,
        transferencias_data: list = None,
        commit: bool = True,
    ) -> Credito:
        """
        =============================================================================
        Method: originate_with_new_client
        Description: Registers a new client and immediately originates a loan for them
                     within the same atomic database transaction.
        =============================================================================
        """
        if issuance_date is None:
            issuance_date = date.today()

        try:
            cuil = client_data.get("cuil")
            if not cuil:
                raise ValueError("Client data must include a valid 'cuil'.")

            # Validate if client already exists to prevent UniqueConstraint violations
            existing_client = self.db.query(Cliente).filter_by(cuil=cuil).first()
            if existing_client:
                self.client = existing_client
            else:
                self.client = Cliente(**client_data)
                self.db.add(self.client)
                self.db.flush()  # Persist client to generate relationships

            cutoff_day = self._get_partner_cutoff_day(partner_id)
            self._generate_credit_and_schedule(
                capital,
                tna_c_iva,
                term,
                partner_id,
                issuance_date,
                due_day,
                cutoff_day,
                type,
                comision_id,
                id_externo,
            )


            if getattr(self.credit, 'comision', None) and getattr(self.credit.comision, 'porcentaje_sellado', 0):
                porcentaje = float(self.credit.comision.porcentaje_sellado)
                if porcentaje > 0:
                    monto_sellado = float(self.credit.capital) * porcentaje
                    t_sellado = Transferencia(
                        credito_id=self.credit.id,
                        cbu=None,
                        monto=monto_sellado,
                        cuit="",
                        razon_social="Sellado"
                    )
                    self.db.add(t_sellado)

            if transferencias_data:
                for t_data in transferencias_data:
                    t_dict = t_data.dict() if hasattr(t_data, 'dict') else t_data
                    transferencia = Transferencia(
                        credito_id=self.credit.id,
                        cbu=t_dict['cbu'],
                        monto=t_dict['monto'],
                        cuit=t_dict['cuit'],
                        razon_social=t_dict['razon_social']
                    )
                    self.db.add(transferencia)

            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return self.credit

        except Exception as e:
            if commit:
                self.db.rollback()
            raise RuntimeError(f"Failed to originate credit with new client: {e}")
