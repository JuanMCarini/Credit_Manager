"""
Module: collections.py
Description: Logic for processing different types of collections (standard,
             early cancellation, and bonuses). Handles the allocation of funds
             across installments using a prioritized waterfall approach.
"""

import enum
from datetime import datetime
from pathlib import Path

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.database.connection import SessionLocal  # noqa: E402
from src.database.models import (  # noqa: E402
    AnticiposSinAplicar,
    Cartera,
    Cliente,
    Cobranza,
    Credito,
    Cuota,
    EstadoCuota,
    SocioComercial,
    TipoCobranzaEnum,
    Proceso,
    TipoProcesoEnum,
    EstadoProcesoEnum,
)
from src.logic.penalties import PenaltyManager  # noqa: E402
from src.utils.dates import normalize_date  # noqa: E402
from src.utils.files import select_file


class IdentificadorEnum(enum.Enum):
    CREDITO_ID = "credito_id"
    ID_EXTERNO = "id_externo"
    CLIENTE_CUIL = "cliente_cuil"
    CLIENTE_DNI = "cliente_dni"
    PROVEEDOR_CUIT = "proveedor_cuit"
    CARTERA_ID = "cartera_id"


class CollectionManager:
    """
    =============================================================================
    Class: CollectionManager
    Description: Orchestrates the allocation of received payments to credit
                 installments. Ensures that payments are applied correctly
                 following financial priority rules (IVA -> Interest -> Capital).
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

    @staticmethod
    def _generate_empty_collections() -> pd.DataFrame:
        """
        =============================================================================
        Method: _generate_empty_collections_df
        Description: Generates an empty pandas DataFrame with the standardized schema
                     for collections. Used as a safe return type for early exits
                     when no installments match the query criteria.
        Returns:
            pd.DataFrame: An empty DataFrame with predefined columns and named index.
        =============================================================================
        """

        return pd.DataFrame(
            columns=[
                "credito_id",
                "nro_cuota",
                "fecha_vencimiento",
                "capital",
                "interes",
                "iva",
                "documento",
                "total",
                "tipo_cobranza",
            ],
            index=pd.Index([], name="id"),
        )

    def _fetch_installments_by_identifier(
        self, identificador: str, val_id: int | str, recurso: bool = False
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: _fetch_installments_by_identifier
        Description: Dynamically constructs and executes an optimized SQL query to
                     retrieve installments (cuotas) based on the provided identifier.
                     Utilizes Python 3.10+ structural pattern matching for highly
                     efficient routing and conditionally applies JOINs.
        Parameters:
            identificador (str): The search dimension (e.g., 'CREDITO_ID', 'CLIENTE_DNI').
            id_val (int | str): The specific value to query against.
        Returns:
            pd.DataFrame: A pandas DataFrame containing the matching installments,
                          indexed by the installment 'id'.
        =============================================================================
        """

        # 1. Iniciamos la query base
        query = self.db.query(Cuota)

        # 2. Ruteo optimizado con match-case, pero encadenando JOINs y WHEREs programáticos
        match identificador:
            case "CREDITO_ID":
                val_id = int(float(val_id))
                query = query.filter(Cuota.credito_id == val_id)

            case "ID_EXTERNO":
                val_id = str(int(float(val_id)))
                query = query.join(Credito).filter(Credito.id_externo == val_id)

            case "CLIENTE_CUIL":
                val_id = str(int(float(val_id)))
                query = query.join(Credito).filter(Credito.cliente_cuil == val_id)

            case "CLIENTE_DNI":
                # SQLAlchemy encadena los joins mágicamente usando las relationships() que ya definiste en models.py
                val_id = str(int(float(val_id)))
                query = (
                    query.join(Credito)
                    .join(Cliente)
                    .filter(Cliente.documento == val_id)
                )
            case "PROVEEDOR_CUIT":
                val_id = str(int(float(val_id)))
                query = (
                    query.join(Credito)
                    .join(Cartera, Credito.cartera_id == Cartera.id)
                    .join(SocioComercial, Cartera.socio_id == SocioComercial.id)
                    .filter(
                        SocioComercial.cuit == val_id,
                        Cartera.recurso == recurso,
                        Cuota.estado.in_([EstadoCuota.PENDIENTE, EstadoCuota.MOROSA]),
                    )
                )

            case _:
                raise ValueError(f"⚠️ '{identificador}' is not a valid identifier type.")

        # 3. Ejecución final
        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")

        return df

    def _calculate_pending_balances(self, df_ctas: pd.DataFrame) -> pd.DataFrame:
        """
        =============================================================================
        Method: _calculate_pending_balances
        Description: Calculates the exact outstanding balances for a given set of
                     installments. It fetches all historical collections linked to
                     these installments, aggregates them, and subtracts them from
                     the original expected values.
                     Filters out completely paid installments and returns a clean,
                     chronologically sorted DataFrame of pending debt.
        Parameters:
            df_ctas (pd.DataFrame): DataFrame of installments indexed by 'id'.
        Returns:
            pd.DataFrame: Sorted DataFrame of pending installments with calculated
                          'total' column.
        =============================================================================
        """
        import pandas as pd

        from sqlalchemy import select
        
        # 1. Preparation of the safe IN clause
        cuotas_ids = list(df_ctas.index)

        # 2. Extraction of historical collections via SQLAlchemy Core API
        stmt = select(Cobranza).where(Cobranza.cuota_id.in_(cuotas_ids))
        df_cobr = pd.read_sql(stmt, self.db.get_bind(), index_col="cuota_id")

        # 3. Grouping and data crossing (Vectorized)
        df_cobr_sum = df_cobr.groupby("cuota_id")[["capital", "interes", "iva"]].sum()
        df = df_ctas.merge(
            df_cobr_sum,
            left_index=True,
            right_index=True,
            how="left",
            suffixes=("", "_cobr"),
        ).fillna(0.0)

        # 4. Calculation of pending balances per component
        for col in ["capital", "interes", "iva"]:
            df[col] -= df[f"{col}_cobr"].round(2)

        # 5. Column cleanup and chronological ordering
        df.drop(columns=["capital_cobr", "interes_cobr", "iva_cobr"], inplace=True)
        df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"])
        df.sort_values(by="fecha_vencimiento", inplace=True)

        # 6. Identification of total balance and filtering of already paid installments
        df["total"] = df[["capital", "interes", "iva"]].sum(axis=1).round(2)
        df_pending = df[df["total"].round(2) != 0.0].copy()

        return df_pending

    def _get_pending_installments(
        self, identificador: str, id_val: int | str, recurso: bool = False
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: _get_pending_installments
        Description: Orchestrates the retrieval and calculation of pending debt.
                     Fetches raw installments, validates business rules (like unique
                     external IDs), calculates remaining balances, and returns the
                     final DataFrame ready for allocation. Returns an empty template
                     if no debt exists.
        Parameters:
            identificador (str): The search dimension (e.g., 'CREDITO_ID').
            id_val (int | str): The specific value to query.
        Returns:
            pd.DataFrame: DataFrame with pending installments, or an empty template.
        =============================================================================
        """
        # 1. Initial installment extraction (using the router)
        df_ctas = self._fetch_installments_by_identifier(identificador, id_val, recurso)

        # If there are no installments at all
        if df_ctas.empty:
            return self._generate_empty_collections()

        # 2. Uniqueness validation for ID_EXTERNO
        match identificador:
            case "ID_EXTERNO":
                if len(df_ctas["credito_id"].unique()) > 1:
                    raise ValueError(
                        f"⚠️ There is more than one credit with external ID {id_val}."
                    )
            case "PROVEEDOR_CUIT":
                if not recurso:
                    raise ValueError(
                        "⚠️ We cannot collect using the CUIT of a supplier where the file is without resources."
                    )

        # 3. Calculation of pending balances
        df = self._calculate_pending_balances(df_ctas)

        # 4. Final verification: if there are installments but they are all already paid
        if df.empty:
            return self._generate_empty_collections()

        return df

    def _persist_collections(
        self, df_cobr: pd.DataFrame, payment_date: datetime, proceso_id: int | None = None, commit: bool = True, descripcion: str | None = None
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: _persist_collections
        Description: Instantiates ORM objects from the processed DataFrame, bulk
                     inserts them into the database, updates the status of all
                     affected credits, and commits the transaction safely.
        Parameters:
            df_cobr (pd.DataFrame): The fully processed collections DataFrame.
            payment_date (datetime | date): The date to stamp on the records.
        Returns:
            pd.DataFrame: The original DataFrame if the transaction succeeds.
        Raises:
            RuntimeError: If the database commit fails, triggers a rollback.
        =============================================================================
        """

        # Create INDIVIDUAL process if no proceso_id is provided
        if not proceso_id:
            proceso = Proceso(
                tipo=TipoProcesoEnum.INDIVIDUAL.value,
                estado=EstadoProcesoEnum.COMPLETADO.value,
                descripcion=descripcion
            )
            self.db.add(proceso)
            self.db.flush()
            proceso_id = proceso.id

        # 1. Instantiate ORM objects in bulk
        for col in ["capital", "interes", "iva"]:
            df_cobr[col] = df_cobr[col].round(2)

        records = []
        for row in df_cobr.itertuples():
            records.append({
                "cuota_id": row.Index,
                "proceso_id": proceso_id,
                "tipo_cobranza": row.tipo_cobranza,
                "capital": row.capital,
                "interes": row.interes,
                "iva": row.iva,
                "fecha": payment_date,
            })

        self.db.bulk_insert_mappings(Cobranza, records)
        self.db.flush()

        # 2. Identify and update all affected credits dynamically
        # This prevents errors if the original search was done by DNI or CUIL
        affected_credits = df_cobr["credito_id"].unique().tolist()
        cuotas_db = (
            self.db.query(Cuota).filter(Cuota.credito_id.in_(affected_credits)).all()
        )
        for cuota in cuotas_db:
            cuota.actualizar_estado(payment_date)

        creditos_db = (
            self.db.query(Credito).filter(Credito.id.in_(affected_credits)).all()
        )
        for credito in creditos_db:
            credito.actualizar_estado()

        # 3. Safe persistence
        if commit:
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise RuntimeError(f"Error persisting the collections transaction: {e}")

        columns = {
            "credito_id": "ID Crédito",
            "nro_cuota": "Nro. Cuota",
            "fecha_vencimiento": "Fecha Vencimiento",
            "capital": "Capital",
            "interes": "Interés",
            "iva": "IVA",
            "documento": "Documento",
            "total": "Total",
            "tipo_cobranza": "Tipo Cobranza",
        }
        df_cobr["Fecha Emisión"] = payment_date
        df_cobr.rename(columns=columns, inplace=True)
        df_cobr.set_index(["ID Crédito", "Nro. Cuota"], inplace=True)
        df_cobr["Fecha Vencimiento"] = pd.to_datetime(
            df_cobr["Fecha Vencimiento"]
        ).dt.to_period("D")
        df_cobr = df_cobr.sort_index()
        df_cobr = df_cobr[
            [
                "Fecha Emisión",
                "Tipo Cobranza",
                "Fecha Vencimiento",
                "Capital",
                "Interés",
                "IVA",
                "Total",
            ]
        ]
        df_cobr.attrs["proceso_id"] = proceso_id
        return df_cobr

    def _process_sobrante_as_penalty(
        self,
        df_cobr: pd.DataFrame,
        sobrante: float,
        payment_date: datetime | str,
        tasa_iva: float = 0.21,
        commit: bool = True,
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: _process_sobrante_as_penalty
        Description: Evaluates if there is a leftover amount (sobrante) and generates
                     a PENALTY credit to absorb it. Safely appends the new penalty
                     installment to the collections DataFrame.
        Parameters:
            df_cobr (pd.DataFrame): The current collections DataFrame.
            sobrante (float): The unused payment amount.
            payment_date (datetime | str): The date of the payment.
            tasa_iva (float): Applicable tax rate.
        Returns:
            pd.DataFrame: The updated DataFrame including the penalty row.
        Raises:
            RuntimeError: If the penalty generation fails.
        =============================================================================
        """
        if sobrante <= 0:
            return df_cobr

        # 1. Share the active session
        new_penalty = PenaltyManager(self.db)

        try:
            # 2. Extract a single valid ID (we take the credit of the last processed installment)
            credito_origen_real = int(df_cobr.iloc[-1]["credito_id"])

            # 3. Generate the credit and installment using the leftover
            penalty_credito, penalty_cuota = new_penalty.generate_penalty_credit(
                credito_origen_id=credito_origen_real,
                monto_punitorio=sobrante,
                fecha_emision=payment_date,
                fecha_vencimiento=payment_date,
                tasa_iva=tasa_iva,
                commit=commit,
            )

            # 4. Add the new row using the installment ID as index
            df_cobr.loc[penalty_cuota.id] = {
                "credito_id": penalty_credito.id,
                "nro_cuota": penalty_cuota.nro_cuota,
                # Keeping pd.Timestamp prevents Pandas TypeError:
                "fecha_vencimiento": pd.Timestamp(penalty_cuota.fecha_vencimiento),
                "capital": penalty_cuota.capital,
                "interes": penalty_cuota.interes,
                "iva": penalty_cuota.iva,
                "tipo_cobranza": TipoCobranzaEnum.PENALTY.value,
                "total": round(
                    penalty_cuota.capital + penalty_cuota.interes + penalty_cuota.iva, 2
                ),
            }

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Critical error generating PENALTY for leftover: {e}")

        return df_cobr

    def process_standard_payment(
        self,
        identificador: str,
        id_val: int | str | None,
        amount: float,
        payment_date: datetime | str | None = None,
        vto_date: datetime | str | None = None,
        tasa_iva: float = 0.21,
        proceso_id: int | None = None,
        commit: bool = True,
    ) -> pd.DataFrame:

        # 1. Normalization
        payment_date = normalize_date(payment_date)
        vto_date = normalize_date(vto_date)

        # 2. Debt extraction and calculation (Early exit if there is no debt)
        df = self._get_pending_installments(identificador, id_val)
        if df.empty:
            return self._generate_empty_collections()

        # 3. Identification of total balance to cover
        df["total_acum"] = df["total"].cumsum().round(2)
        df_cobr = df[df["total_acum"] <= amount].copy()

        cobr = df_cobr["total"].sum()
        unuse_amount = round(amount - cobr, 2)

        # 4. Financial waterfall for leftover balance (partial allocation)
        if unuse_amount > 0:
            pending_rows = df[df["total_acum"] > amount]

            if not pending_rows.empty:
                partial_df = pending_rows.iloc[[0]].copy()
                row = partial_df.index.values[0]
                partial_df.loc[row, "total"] = unuse_amount

                if unuse_amount < partial_df.loc[row, "interes"]:
                    partial_df.loc[row, "interes"] = round(
                        unuse_amount / (1 + tasa_iva), 2
                    )
                    partial_df.loc[row, "iva"] = round(
                        unuse_amount - partial_df.loc[row, "interes"], 2
                    )
                    partial_df.loc[row, "capital"] = 0.0
                else:
                    partial_df.loc[row, "capital"] = unuse_amount - (
                        partial_df.loc[row, ["interes", "iva"]].sum()
                    )

                df_cobr = pd.concat([df_cobr, partial_df], axis=0)

        # 5. Cleanup of temporary columns
        if "total_acum" in df_cobr.columns:
            df_cobr.drop(columns=["total_acum"], inplace=True)

        # 6. Classification of collection type
        df_cobr["tipo_cobranza"] = np.where(
            df_cobr["fecha_vencimiento"] <= pd.Timestamp(vto_date),
            TipoCobranzaEnum.COMUN.value,
            TipoCobranzaEnum.ANTICIPO.value,
        )

        sobrante = round(amount - df_cobr["total"].sum(), 2)

        # We delegate the penalty creation (if leftover is 0, the function returns the intact DF)
        df_cobr = self._process_sobrante_as_penalty(
            df_cobr, sobrante, payment_date, tasa_iva, commit=commit
        )

        # 7. Final delegated persistence
        return self._persist_collections(df_cobr, payment_date, proceso_id=proceso_id, commit=commit, descripcion=f"{identificador}: {id_val}")

    def process_early_cancellation(
        self,
        identificador: str,
        id_val: int | str | None,
        amount: float,
        payment_date: datetime | str | None = None,
        vto_date: datetime | str | None = None,
        tasa_iva: float = 0.21,
        proceso_id: int | None = None,
        commit: bool = True,
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: process_early_cancellation
        Description: Handles total or partial early cancellation. Usually prioritizes
                     capital reduction and may involve interest waivers.
        =============================================================================
        """

        # 1. Normalization
        payment_date = normalize_date(payment_date)
        vto_date = normalize_date(vto_date)

        # 2. Debt extraction and calculation (Early exit if there is no debt)
        df = self._get_pending_installments(identificador, id_val)
        if df.empty:
            return df

        # 3. Identification of total balance to cover

        a_vencer = df["fecha_vencimiento"] > vto_date
        df_BCA = df.loc[a_vencer].copy()
        df.loc[a_vencer, ["interes", "iva"]] = [0.0, 0.0]
        df["total"] = df[["capital", "interes", "iva"]].sum(axis=1)

        df["total_acum"] = df["total"].cumsum().round(2)
        df_cobr = df[df["total_acum"] <= amount].copy()

        cobr = df_cobr["total"].sum()
        unuse_amount = round(amount - cobr, 2)

        # 4. Financial waterfall for leftover balance (partial allocation)
        if unuse_amount > 0:
            pending_rows = df[df["total_acum"] > amount]

            if not pending_rows.empty:
                partial_df = pending_rows.iloc[[0]].copy()
                row = partial_df.index.values[0]
                partial_df.loc[row, "total"] = unuse_amount

                if unuse_amount < partial_df.loc[row, "interes"]:
                    partial_df.loc[row, "interes"] = round(
                        unuse_amount / (1 + tasa_iva), 2
                    )
                    partial_df.loc[row, "iva"] = round(
                        unuse_amount - partial_df.loc[row, "interes"], 2
                    )
                    partial_df.loc[row, "capital"] = 0.0
                else:
                    partial_df.loc[row, "capital"] = unuse_amount - (
                        partial_df.loc[row, ["interes", "iva"]].sum()
                    )

                df_cobr = pd.concat([df_cobr, partial_df], axis=0)

        # 5. Cleanup of temporary columns
        if "total_acum" in df_cobr.columns:
            df_cobr.drop(columns=["total_acum"], inplace=True)

        # 6. Classification of collection type
        df_cobr["tipo_cobranza"] = np.where(
            df_cobr["fecha_vencimiento"] <= pd.Timestamp(vto_date),
            TipoCobranzaEnum.COMUN.value,
            TipoCobranzaEnum.CA.value,
        )

        sobrante = round(amount - df_cobr["total"].sum(), 2)
        df_BCA = df_BCA.merge(
            df_cobr["capital"], left_index=True, right_index=True, suffixes=("", "_BCA")
        )
        df_BCA["capital"] -= df_BCA["capital_BCA"]
        df_BCA.drop(columns=["capital_BCA"], inplace=True)
        df_BCA = df_BCA.loc[df_BCA["capital"] == 0.0]
        df_BCA["total"] = df_BCA[["capital", "interes", "iva"]].sum(axis=1)

        if not df_BCA.empty:
            df_BCA["tipo_cobranza"] = TipoCobranzaEnum.BCA.value
            df_cobr = pd.concat([df_cobr, df_BCA])

        # We delegate the penalty creation (if leftover is 0, the function returns the intact DF)
        df_cobr = self._process_sobrante_as_penalty(
            df_cobr, sobrante, payment_date, tasa_iva, commit=commit
        )

        # 7. Final delegated persistence
        return self._persist_collections(df_cobr, payment_date, proceso_id=proceso_id, commit=commit, descripcion=f"{identificador}: {id_val}")

    def process_resource(
        self,
        identificador: str,
        id_val: int | str,
        amount: float,
        payment_date: str | datetime,
        proceso_id: int | None = None,
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: process_resource
        Description: Processes wholesale institutional resource collections. Tracks
                     historical advances (anticipos), updates the available cash
                     pool, filters fully covered installments ordered by due date,
                     persists collections under RECURSO type, and stores any
                     leftover amount as a new partner advance. Safe against DB locks.
        Parameters:
            payment_date (str | datetime): The settlement transaction date.
            amount (float): Raw cash amount received from the partner.
            id_val (int | str): The identification value (CUIT or Portfolio ID).
            identificador (str): The dimension type (defaults to 'PROVEEDOR_CUIT').
        Returns:
            pd.DataFrame: Processed collections breakdown template or an empty template.
        =============================================================================
        """

        from src.database.models import TipoCobranzaEnum

        payment_date = normalize_date(payment_date)
        id_tipo = identificador.upper()

        try:
            # 1. Dynamic query construction to query historical advances
            query_anticipos = self.db.query(AnticiposSinAplicar)
            match identificador:
                case "PROVEEDOR_CUIT":
                    id_val = str(id_val)
                    query_anticipos = (
                        query_anticipos.join(
                            SocioComercial,
                            AnticiposSinAplicar.socio_id == SocioComercial.id,
                        )
                        .join(Cartera, SocioComercial.id == Cartera.socio_id)
                        .filter(SocioComercial.cuit == id_val)
                    )
                case "CARTERA_ID":
                    id_val = int(id_val)
                    query_anticipos = query_anticipos.join(
                        Cartera, AnticiposSinAplicar.socio_id == Cartera.socio_id
                    ).filter(Cartera.id == id_val)
            query_anticipos = query_anticipos.filter(Cartera.recurso)
            # 2. Reading existing advances and adding to the available amount
            anticipos = pd.read_sql(
                query_anticipos.statement,
                self.db.get_bind(),
                index_col="id",
            )

            monto_anticipos = (
                float(anticipos["monto"].sum()) if "monto" in anticipos.columns else 0.0
            )
            amount += monto_anticipos
            # 3. Extraction and calculation of filtered current debt
            df = self._fetch_installments_by_identifier(identificador, id_val, True)
            df = self._calculate_pending_balances(df)

            # 4. Chronological grouping by due date to determine total coverage
            df_vto = df.groupby("fecha_vencimiento")[["total"]].sum().sort_index()
            df_vto["total_acum"] = df_vto["total"].cumsum().round(2)
            df_vto = df_vto[df_vto["total_acum"] <= amount]
            sobrante = round(amount - df_vto["total"].sum() - monto_anticipos, 2)

            # 5. Filtering of installments falling within fully covered due dates
            df = df.loc[df["fecha_vencimiento"].isin(df_vto.index)].copy()

            # 6. Persistence of the remainder (leftover) in the partner advances table
            if sobrante != 0:
                fecha_iso = normalize_date(payment_date, as_type=str)
                if id_tipo == "PROVEEDOR_CUIT":
                    self.db.execute(
                        text("""
                            INSERT INTO anticipos_socios (socio_id, monto, fecha)
                            SELECT id, :monto, :fecha FROM socios_comerciales WHERE cuit = :cuit
                        """),
                        {"monto": sobrante, "fecha": fecha_iso, "cuit": id_val},
                    )
                elif id_tipo == "CARTERA_ID":
                    self.db.execute(
                        text("""
                            INSERT INTO anticipos_socios (socio_id, cartera_id, monto, fecha)
                            SELECT socio_id, id, :monto, :fecha FROM carteras WHERE id = :cartera_id
                        """),
                        {
                            "monto": sobrante,
                            "fecha": fecha_iso,
                            "cartera_id": id_val,
                        },
                    )
                self.db.flush()

            # 7. Guard clause: If no installments are collected, save the advance and exit
            if df.empty:
                self.db.commit()
                return self._generate_empty_collections()

            # 8. Final classification of collection type and delegation of persistence (which includes commit)
            df["tipo_cobranza"] = TipoCobranzaEnum.RECURSO.value
            return self._persist_collections(df, payment_date, proceso_id=proceso_id, descripcion=f"{identificador}: {id_val}")

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error processing partner resources: {e}")

    def process_massive_collection(
        self,
        identificador: str,
        id_column: str = "A",
        amount_column: str = "B",
        payment_date: str | datetime | None = None,
        vto_date: str | datetime | None = None,
        path: str | Path | None = None,
        early: bool = False,
        file_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> pd.DataFrame:

        if payment_date is None:
            payment_date = datetime.today()
        if vto_date is None:
            vto_date = datetime.today()

        if file_bytes is not None:
            import io
            data_source = io.BytesIO(file_bytes)
        elif path is not None:
            data_source = path
        else:
            data_source = select_file()

        match identificador:
            case "CREDITO_ID":
                ident = "credito_id"
            case "CLIENTE_CUIL":
                ident = "cliente_cuil"
            case "CLIENTE_DNI":
                ident = "cliente_dni"
            case "ID_EXTERNO":
                ident = "id_externo"
            case "PROVEEDOR_CUIT":
                ident = "proveedor_cuit"
            case "CARTERA_ID":
                ident = "cartera_id"
            case _:
                raise ValueError(
                    f"Identificador '{identificador}' no soportado para cobros masivos."
                )

        # By passing a single comma-separated string, Pandas treats them as Excel column letters (A, B, N, etc)
        # instead of literal column header names.
        df = pd.read_excel(data_source, usecols=f"{id_column},{amount_column}")
        header = [ident, "monto"]
        df.columns = header
        df["monto"] = df["monto"].astype(float)
        df = df.loc[df[ident] != "Total"]
        df[ident] = df[ident].astype(str)
        df = df.groupby(ident)[["monto"]].sum().reset_index()

        if (df["monto"] >= 0).all() or (df["monto"] <= 0).all():
            df["monto"] = df["monto"].abs()
        else:
            raise ValueError("Amounts with different signs.")

        lista_cobranzas = []
        problems = []
        if early:
            process = self.process_early_cancellation
        else:
            process = self.process_standard_payment

        try:
            proceso_masivo = Proceso(
                tipo=TipoProcesoEnum.MASIVO_CSV.value,
                estado=EstadoProcesoEnum.PROCESANDO.value,
                descripcion=filename or "Proceso Masivo"
            )
            self.db.add(proceso_masivo)
            self.db.flush()
            p_id = proceso_masivo.id

            for i, row in df.iterrows():
                new_cobr = process(
                    identificador,
                    row[ident],
                    row["monto"],
                    payment_date,
                    vto_date,
                    proceso_id=p_id,
                    commit=False,
                )
                if not new_cobr.empty:
                    lista_cobranzas.append(new_cobr)
                else:
                    problems.append(row[ident])

            if problems:
                self.db.rollback()
                df_prob = df.loc[df[ident].isin(problems)]
                raise ValueError(
                    f"Se encontraron problemas al procesar las siguientes filas: {problems}. Se aplicó un rollback total."
                )

            proceso_masivo.estado = EstadoProcesoEnum.COMPLETADO.value
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

        df_cobr = pd.concat(lista_cobranzas) if lista_cobranzas else pd.DataFrame()
        df_cobr.attrs["proceso_id"] = p_id
        return df_cobr
