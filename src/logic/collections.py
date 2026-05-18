"""
Module: collections.py
Description: Logic for processing different types of collections (standard,
             early cancellation, and bonuses). Handles the allocation of funds
             across installments using a prioritized waterfall approach.
"""

import enum
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import Cobranza, Credito, Cuota, TipoCobranzaEnum
from src.logic.penalties import PenaltyManager
from src.utils.dates import normalize_date


class IdentificadorEnum(enum.Enum):
    CREDITO_ID = "credito_id"
    ID_EXTERNO = "id_externo"
    CLIENTE_CUIT = "cliente_cuit"
    CLIENTE_DNI = "cliente_dni"


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
        self, identificador: str, id_val: int | str
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
        import pandas as pd

        columns = "c.*"
        joins = ""

        # Enrutador optimizado con match-case
        match identificador:
            case "CREDITO_ID":
                where = " WHERE c.credito_id = :val_id"

            case "ID_EXTERNO":
                columns += ", cr.id_externo, cr.cliente_cuil"
                joins = " JOIN creditos cr ON c.credito_id = cr.id"
                where = " WHERE cr.id_externo = :val_id"

            case "CLIENTE_CUIL":
                columns += ", cr.id_externo, cr.cliente_cuil"
                joins = " JOIN creditos cr ON c.credito_id = cr.id"
                where = " WHERE cr.cliente_cuil = :val_id"

            case "CLIENTE_DNI":
                columns += ", cl.documento"
                joins = " JOIN creditos cr ON c.credito_id = cr.id JOIN clientes cl ON cr.cliente_cuil = cl.cuil"
                where = " WHERE cl.documento = :val_id"

            case _:
                raise ValueError(
                    f"⚠️ '{identificador}' no es un tipo válido de identificador."
                )

        # Armado final de la query
        ctas_query = text(f"SELECT {columns} FROM cuotas c {joins} {where}")

        # Ejecución segura delegando el parámetro al motor SQL
        return pd.read_sql(
            ctas_query, self.db.get_bind(), params={"val_id": id_val}, index_col="id"
        )

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
        from sqlalchemy import text

        # 1. Preparación de la cláusula IN segura
        cuotas_ids = tuple(df_ctas.index)
        in_clause = f"({cuotas_ids[0]})" if len(cuotas_ids) == 1 else str(cuotas_ids)

        # 2. Extracción de cobranzas históricas
        cobr_query = text(f"SELECT * FROM cobranzas WHERE cuota_id IN {in_clause}")
        df_cobr = pd.read_sql(cobr_query, self.db.get_bind(), index_col="cuota_id")

        # 3. Agrupación y cruce de datos (Vectorizado)
        df_cobr_sum = df_cobr.groupby("cuota_id")[["capital", "interes", "iva"]].sum()
        df = df_ctas.merge(
            df_cobr_sum,
            left_index=True,
            right_index=True,
            how="left",
            suffixes=("", "_cobr"),
        ).fillna(0.0)

        # 4. Cálculo de saldos pendientes por componente
        for col in ["capital", "interes", "iva"]:
            df[col] -= df[f"{col}_cobr"]

        # 5. Limpieza de columnas y ordenamiento cronológico
        df.drop(columns=["capital_cobr", "interes_cobr", "iva_cobr"], inplace=True)
        df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"])
        df.sort_values(by="fecha_vencimiento", inplace=True)

        # 6. Identificación del saldo total y filtrado de cuotas ya canceladas
        df["total"] = df[["capital", "interes", "iva"]].sum(axis=1)
        df_pending = df[df["total"].round(2) != 0.0].copy()

        return df_pending

    def _get_pending_installments(
        self, identificador: str, id_val: int | str
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
        # 1. Extracción inicial de cuotas (usando el enrutador)
        df_ctas = self._fetch_installments_by_identifier(identificador, id_val)

        # Si no hay cuotas en absoluto
        if df_ctas.empty:
            return self._generate_empty_collections_df()

        # 2. Validación de unicidad para ID_EXTERNO
        if identificador == "ID_EXTERNO":
            if len(df_ctas["credito_id"].unique()) > 1:
                raise ValueError(f"⚠️ Hay más de un crédito con ID externo {id_val}.")

        # 3. Cálculo de saldos pendientes
        df = self._calculate_pending_balances(df_ctas)

        # 4. Verificación final: si hay cuotas pero ya están todas pagadas
        if df.empty:
            return self._generate_empty_collections_df()

        return df

    def _persist_collections(
        self, df_cobr: pd.DataFrame, payment_date: datetime
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

        # 1. Instanciar objetos ORM en bloque
        new_collections = []
        for row in df_cobr.itertuples():
            cobranza = Cobranza(
                cuota_id=row.Index,
                tipo_cobranza=row.tipo_cobranza,
                capital=row.capital,
                interes=row.interes,
                iva=row.iva,
                fecha=payment_date,
            )
            new_collections.append(cobranza)

        self.db.add_all(new_collections)
        self.db.flush()

        # 2. Identificar y actualizar todos los créditos afectados de forma dinámica
        # Esto previene errores si la búsqueda original se hizo por DNI o CUIL
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

        # 3. Persistencia segura
        try:
            self.db.commit()

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
            return df_cobr
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error persistiendo la transacción de cobranzas: {e}")

    def process_standard_payment(
        self,
        identificador: str,
        id_val: int | str | None,
        amount: float,
        payment_date: datetime | str | None = None,
        tasa_iva: float = 0.21,
    ) -> pd.DataFrame:

        # 1. Normalización
        payment_date = normalize_date(payment_date)

        # 2. Extracción y cálculo de deuda (Salida temprana si no hay deuda)
        df = self._get_pending_installments(identificador, id_val)
        if df.empty:
            return df

        # 3. Identificación del saldo total a cubrir
        df["total_acum"] = df["total"].cumsum().round(2)
        df_cobr = df[df["total_acum"] <= amount].copy()

        cobr = df_cobr["total"].sum()
        unuse_amount = round(amount - cobr, 2)

        # 4. Cascada financiera para saldo sobrante (imputación parcial)
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

        # 5. Limpieza de columnas temporales
        if "total_acum" in df_cobr.columns:
            df_cobr.drop(columns=["total_acum"], inplace=True)

        # 6. Clasificación del tipo de cobranza
        df_cobr["tipo_cobranza"] = np.where(
            df_cobr["fecha_vencimiento"] <= pd.Timestamp(payment_date),
            TipoCobranzaEnum.COMUN.value,
            TipoCobranzaEnum.ANTICIPO.value,
        )

        sobrante = round(amount - df_cobr["total"].sum(), 2)

        if sobrante > 0:
            # 1. Share the existing active session (Do NOT use 'with')
            new_penalty = PenaltyManager(self.db)

            try:
                # 2. Extract a single valid integer ID from the processed collections
                credito_origen_real = [
                    int(id_cred) for id_cred in df_cobr["credito_id"].unique()
                ]

                # 3. Generate the credit and quota using the actual sobrante (not 121)
                penalty_credito, penalty_cuota = new_penalty.generate_penalty_credit(
                    credito_origen_id=credito_origen_real,
                    monto_punitorio=sobrante,
                    fecha_emision=payment_date,
                    fecha_vencimiento=payment_date,
                    tasa_iva=tasa_iva,
                )

                # 4. INSIDE THE TRY: Only append if the generation was successful
                df_cobr.loc[len(df_cobr) + 1] = {
                    "credito_id": penalty_credito.id,
                    "nro_cuota": penalty_cuota.nro_cuota,
                    "fecha_vencimiento": str(penalty_cuota.fecha_vencimiento),
                    "capital": penalty_cuota.capital,
                    "interes": penalty_cuota.interes,
                    "iva": penalty_cuota.iva,
                    "tipo_cobranza": TipoCobranzaEnum.PENALTY.value,
                    "total": round(
                        penalty_cuota.capital
                        + penalty_cuota.interes
                        + penalty_cuota.iva,
                        2,
                    ),
                }

            except Exception as e:
                self.db.rollback()
                raise RuntimeError(
                    f"Critical error generating PENALTY for sobrante: {e}"
                )

        # 7. Persistencia final delegada
        return self._persist_collections(df_cobr, payment_date)

    def process_early_cancellation(
        self,
        identificador: str,
        id_val: int | str | None,
        amount: float,
        payment_date: datetime | str | None = None,
        tasa_iva: float = 0.21,
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: process_early_cancellation
        Description: Handles total or partial early cancellation. Usually prioritizes
                     capital reduction and may involve interest waivers.
        =============================================================================
        """
        # Aquí iría la lógica para TipoCobranzaEnum.CA y TipoCobranzaEnum.BCA
        # Esta lógica suele requerir que el usuario defina si se bonifican intereses futuros.
        pass
