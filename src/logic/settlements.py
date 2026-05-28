"""
Module: settlements.py
Description: Logic for processing and settling payments to portfolio buyers.
             Cross-references client collections (Cobranzas) with sold installments
             to calculate and generate liabilities (LiquidacionCuotaCedida).
Author: Juan Martín Carini
Date: 2026-05-21
"""

import enum
from datetime import date, datetime
from typing import Optional, Union

import pandas as pd
from IPython.display import display
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import (
    Cartera,
    Cobranza,
    Cuota,
    EstadoCuotaCedida,
    LiquidacionCuotaCedida,
    OperacionCartera,
    SocioComercial,
    TipoLiquidacionEnum,
)
from src.utils.dates import normalize_date


class IdentificadorEnum(enum.Enum):
    CLIENTE_ID = "CLIENTE ID"
    CLIENTE_CUIT = "CLIENTE CUIT"
    CARTERA_ID = "CARTERA ID"


class SettlementManager:
    """
    =============================================================================
    Class: SettlementManager
    Description: Orchestrates the generation of LiquidacionCuotaCedida records.
                 It scans for installments that were sold to third parties,
                 checks how much money was collected from the end-user, and
                 renders the corresponding amounts to the portfolio buyer.
    =============================================================================
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initializes the settlement manager with an active database session.
        """
        self.db = db_session or SessionLocal()
        self._own_session = db_session is None
        self.settlements = None

    def obtain_uncancelled_installments(
        self,
        id_val: int | str | list | IdentificadorEnum,
        identificador: str = "CLIENTE ID",
        fecha: Union[str, date, datetime, None] = None,
        fecha_vencimiento_desde: Union[str, date, datetime, None] = None,
        fecha_vencimiento_hasta: Union[str, date, datetime, None] = None,
    ) -> pd.DataFrame:

        if type(id_val) is not list:
            id_val = [id_val]
        fecha = normalize_date(fecha, str)

        query = (
            self.db.query(
                Cuota,
                Cartera.id.label("cartera_id"),
                Cartera.recurso,
                Cartera.iva.label("cartera_iva"),
            )
            .join(OperacionCartera, Cuota.id == OperacionCartera.cuota_id)
            .join(Cartera, OperacionCartera.cartera_id == Cartera.id)
            .filter(OperacionCartera.fecha_registro <= fecha)
            .filter(
                Cuota.estado_cesion.in_(
                    [EstadoCuotaCedida.MOROSA, EstadoCuotaCedida.PENDIENTE]
                )
            )
            .filter(
                OperacionCartera.fecha_registro
                == self.db.query(
                    func.max(OperacionCartera.fecha_registro)
                ).scalar_subquery()
            )
        )
        if fecha_vencimiento_desde:
            fecha_vencimiento_desde = normalize_date(fecha_vencimiento_desde)
            query = query.filter(Cuota.fecha_vencimiento >= fecha_vencimiento_desde)
        if fecha_vencimiento_hasta:
            fecha_vencimiento_hasta = normalize_date(fecha_vencimiento_hasta)
            query = query.filter(Cuota.fecha_vencimiento <= fecha_vencimiento_hasta)

        match identificador:
            case "CLIENTE_ID":
                query = query.filter(Cartera.id.in_(id_val))

        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df.loc[~df["cartera_iva"], "iva"] == 0.0
        return df.sort_values(by=["fecha_vencimiento", "credito_id", "nro_cuota"])

    def obtain_pending_settlement(self) -> pd.DataFrame:

        query = (
            self.db.query(
                LiquidacionCuotaCedida,
                Cuota.fecha_vencimiento,
                SocioComercial.razon_social,
                Cartera.recurso,
            )
            .join(Cuota, LiquidacionCuotaCedida.cuota_id == Cuota.id)
            .join(Cartera, LiquidacionCuotaCedida.cartera_id == Cartera.id)
            .join(SocioComercial, Cartera.socio_id == SocioComercial.id)
            .filter(
                LiquidacionCuotaCedida.tipo_liquidacion == TipoLiquidacionEnum.PENDIENTE
            )
        )
        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df_group = df.groupby(["razon_social", "fecha_vencimiento"])[
            ["capital", "interes", "iva"]
        ].sum()
        df_group["total"] = df_group[["capital", "interes", "iva"]].sum(axis=1)
        display(df_group.map("$ {:,.2f}".format))

        return df

    def obtain_settlement_of_transferred_quota(
        self,
        id_val: int | str | list | IdentificadorEnum,
        identificador: str = "CLIENTE ID",
        fecha: Union[str, date, datetime, None] = None,
        fecha_vencimiento_desde: Union[str, date, datetime, None] = None,
        fecha_vencimiento_hasta: Union[str, date, datetime, None] = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:

        df_ctas = self.obtain_uncancelled_installments(
            id_val,
            identificador,
            fecha,
            fecha_vencimiento_desde,
            fecha_vencimiento_hasta,
        )

        query = self.db.query(LiquidacionCuotaCedida).filter(
            LiquidacionCuotaCedida.cuota_id.in_(df_ctas.index)
        )
        df_sett = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")

        df_sett = df_sett.groupby("cuota_id")[["capital", "interes", "iva"]].sum()
        df = df_ctas.merge(
            df_sett,
            left_index=True,
            right_index=True,
            how="left",
            suffixes=("", "_sett"),
        )
        df[["capital_sett", "interes_sett", "iva_sett"]] = df[
            ["capital_sett", "interes_sett", "iva_sett"]
        ].fillna(0.0)

        for col in ["capital", "interes", "iva"]:
            df[col] -= df[f"{col}_sett"]
            df.drop(columns=[f"{col}_sett"], inplace=True)

        df_recurso = df.loc[df["recurso"]]
        df_s_recurso = df.loc[~df["recurso"]]

        return df_recurso, df_s_recurso

    def settlements_resource(self, df_rec: pd.DataFrame):

        df = df_rec.reset_index().copy()
        df = df.loc[df[["capital", "interes", "iva"]].sum(axis=1) != 0].copy()
        df.rename(columns={"id": "cuota_id"}, inplace=True)
        df["tipo_liquidacion"] = TipoLiquidacionEnum.RECURSO
        df = df[
            ["cuota_id", "cartera_id", "tipo_liquidacion", "capital", "interes", "iva"]
        ]

        self.settlements = df

        return df

    def settlements_s_resource(self, df_s_rec: pd.DataFrame):

        df_s_rec = df_s_rec.sort_index()
        display(df_s_rec.head(2))
        query = self.db.query(Cobranza).filter(
            Cobranza.cuota_id.in_(df_s_rec.index.unique())
        )
        df_cobr = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df_cobr = df_cobr.sort_values(by="cuota_id")
        return df_cobr

    def execute_settlements(self, fecha_pago: Union[str, date, datetime, None]):

        fecha_pago = normalize_date(fecha_pago, date)

        new_settlements = []
        for row in self.settlements.itertuples():
            new_sett = LiquidacionCuotaCedida(
                cuota_id=row.cuota_id,
                cartera_id=row.cartera_id,
                tipo_liquidacion=row.tipo_liquidacion,
                capital=row.capital,
                interes=row.interes,
                iva=row.iva,
                fecha_pago=fecha_pago,
            )
            new_settlements.append(new_sett)
        self.db.add_all(new_settlements)
        self.db.flush()

        cuotas_afectadas = self.settlements["cuota_id"].unique().tolist()
        cuotas_db = self.db.query(Cuota).filter(Cuota.id.in_(cuotas_afectadas)).all()
        for cuota in cuotas_db:
            cuota.actualizar_estado_cedido(fecha_pago)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error persisting the settlements transaction: {e}")

    def __del__(self):
        """
        Safely closes the database session if it was created internally.
        """
        if hasattr(self, "_own_session") and self._own_session and hasattr(self, "db") and self.db:
            self.db.close()
