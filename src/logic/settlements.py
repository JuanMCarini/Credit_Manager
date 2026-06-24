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
from sqlalchemy import func, text
from sqlalchemy import not_
from sqlalchemy.orm import Session, aliased

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
    TipoOperacionCartera,
    TipoCobranzaEnum,
    Proceso,
    TipoProcesoEnum,
    EstadoProcesoEnum
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
        self.fecha_corte = None

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
        fecha = normalize_date(fecha, date)
        self.fecha_corte = fecha
        
        op_cartera_sub = aliased(OperacionCartera)
        subquery = (
            self.db.query(func.max(op_cartera_sub.fecha_registro))
            .filter(op_cartera_sub.cuota_id == Cuota.id)
            .filter(op_cartera_sub.fecha_registro <= fecha)
            .filter(Cartera.tipo_operacion == TipoOperacionCartera.VENTA)
            .scalar_subquery()
        )

        query = (
            self.db.query(
                Cuota,
                Cartera.id.label("cartera_id"),
                Cartera.recurso,
                Cartera.iva.label("cartera_iva"),
            )
            .join(OperacionCartera, Cuota.id == OperacionCartera.cuota_id)
            .join(Cartera, OperacionCartera.cartera_id == Cartera.id)
            .filter(OperacionCartera.fecha_registro == subquery)
            .filter(
                Cuota.estado_cesion.in_(
                    [EstadoCuotaCedida.MOROSA, EstadoCuotaCedida.PENDIENTE]
                )
            )
        )
        if fecha_vencimiento_desde:
            fecha_vencimiento_desde = normalize_date(fecha_vencimiento_desde)
            query = query.filter(Cuota.fecha_vencimiento >= fecha_vencimiento_desde)
        if fecha_vencimiento_hasta:
            fecha_vencimiento_hasta = normalize_date(fecha_vencimiento_hasta)
            query = query.filter(Cuota.fecha_vencimiento <= fecha_vencimiento_hasta)

        match identificador:
            case "CLIENTE_ID" | "Socio ID":
                id_val_int = [int(i) for i in id_val if str(i).isdigit()]
                query = query.filter(Cartera.socio_id.in_(id_val_int))
            case "CLIENTE_CUIT" | "Socio CUIT":
                query = (query
                .join(SocioComercial, Cartera.socio_id == SocioComercial.id)
                .filter(SocioComercial.cuit.in_(id_val)))

        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df.loc[~df["cartera_iva"], "iva"] = 0.0

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
            .filter(Cartera.tipo_operacion == TipoOperacionCartera.VENTA)
            .join(SocioComercial, Cartera.socio_id == SocioComercial.id)
            .filter(LiquidacionCuotaCedida.cancelada == False)
        )

        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        if "tipo_liquidacion" in df.columns:
            df["tipo_liquidacion"] = df["tipo_liquidacion"].apply(lambda x: getattr(x, "value", x))
        df_group = df.groupby(["razon_social", "fecha_vencimiento", "tipo_liquidacion"])[
            ["capital", "interes", "iva"]
        ].sum()
        df_group["total"] = df_group[["capital", "interes", "iva"]].sum(axis=1)
        print(df_group.map("$ {:,.2f}".format))

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
        df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"]).dt.date
        df["cobranza_id"] = None
        df = df[
            ["cuota_id", "credito_id", "cartera_id", "tipo_liquidacion", "nro_cuota", "fecha_vencimiento", "capital", "interes", "iva", "cobranza_id"]
        ]

        self.settlements = df

        return df

    def settlements_s_resource(self, df_s_rec: pd.DataFrame):

        df_s_rec = df_s_rec.sort_index()
        
        # Exclude collections that have already been settled
        settled_ids = (
            self.db.query(LiquidacionCuotaCedida.cobranza_id)
            .filter(LiquidacionCuotaCedida.cobranza_id.isnot(None))
            .scalar_subquery()
        )

        query = self.db.query(Cobranza).filter(
            Cobranza.cuota_id.in_(df_s_rec.index.unique()),
            not_(Cobranza.id.in_(settled_ids))
        )

        df_cobr = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df_cobr = df_cobr.sort_values(by="cuota_id")
        df_cobr = df_cobr.merge(df_s_rec[["fecha_vencimiento", "nro_cuota", "credito_id", "cartera_iva", "cartera_id"]], left_on="cuota_id", right_index=True)
        df_cobr["fecha_vencimiento"] = pd.to_datetime(df_cobr["fecha_vencimiento"])
        df_cobr.loc[~df_cobr["cartera_iva"], "iva"] = 0.0
        df_cobr["total"] = df_cobr[["capital", "interes", "iva"]].sum(axis=1)
        
        df_cobr["tipo_liquidacion"] = TipoLiquidacionEnum.NORMAL
        
        mask = df_cobr["tipo_cobranza"] == TipoCobranzaEnum.BCA
        df_cobr.loc[mask, "tipo_liquidacion"] = TipoLiquidacionEnum.BCA

        mask = mask & (df_cobr["fecha_vencimiento"].dt.to_period("M") <= pd.Period(self.fecha_corte, freq="M"))
        df_cobr.loc[mask, "tipo_liquidacion"] = TipoLiquidacionEnum.IP

        mask = (df_cobr["tipo_cobranza"] == TipoCobranzaEnum.CA)
        df_cobr.loc[mask, "tipo_liquidacion"] = TipoLiquidacionEnum.CA

        df_cobr = df_cobr[self.settlements.columns.drop("cobranza_id")].reset_index()
        df_cobr.rename(columns={"id": "cobranza_id"}, inplace=True)
        df_cobr["fecha_vencimiento"] = pd.to_datetime(df_cobr["fecha_vencimiento"]).dt.date
        df_cobr = df_cobr[self.settlements.columns]

        self.settlements = pd.concat([self.settlements, df_cobr], ignore_index=True)

        return df_cobr

    def execute_settlements(self, fecha_pago: Union[str, date, datetime, None], cancelada: bool=False, proceso_id: int | None = None):

        if cancelada:
            fecha_pago = normalize_date(fecha_pago, date)
        else:
            fecha_pago = None

        if not proceso_id:
            proceso_estado = EstadoProcesoEnum.COMPLETADO.value if cancelada else EstadoProcesoEnum.PENDIENTE.value
            proceso = Proceso(
                tipo=TipoProcesoEnum.LIQUIDACIONES_MASIVAS.value,
                estado=proceso_estado,
                descripcion="Liquidación Masiva"
            )
            self.db.add(proceso)
            self.db.flush()
            proceso_id = proceso.id

        new_settlements = []
        for row in self.settlements.itertuples():
            cobranza_id = None
            if hasattr(row, "cobranza_id") and pd.notna(row.cobranza_id):
                cobranza_id = int(row.cobranza_id)

            new_sett = LiquidacionCuotaCedida(
                cuota_id=row.cuota_id,
                cartera_id=row.cartera_id,
                tipo_liquidacion=row.tipo_liquidacion,
                capital=row.capital,
                interes=row.interes,
                iva=row.iva,
                fecha_pago=fecha_pago,
                cancelada=cancelada,
                cobranza_id=cobranza_id,
                proceso_id=proceso_id
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

    def canceled_settlements(
        self, 
        fecha_pago: Union[str, date, datetime, None]=None, 
        amount: float=0, 
        proceso_id: Optional[int]=None,
        tipos_liquidacion: Optional[list] = None
    ):

        fecha_pago = normalize_date(fecha_pago, date)
        query = (
            self.db.query(LiquidacionCuotaCedida)
            .filter(LiquidacionCuotaCedida.cancelada == False)
        )
        if proceso_id is not None:
            query = query.filter(LiquidacionCuotaCedida.proceso_id == proceso_id)
            
        if tipos_liquidacion is not None:
            query = query.filter(LiquidacionCuotaCedida.tipo_liquidacion.in_(tipos_liquidacion))

        df = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        if df.empty:
            return df, amount, 0

        for col in ["capital", "interes", "iva"]:
            df[col] = df[col].astype(float)

        cancel_all = (amount == 0)
        cuotas_afectadas = set()
        cantidad_canceladas = 0
        
        for i, row in df.iterrows():
            total_row = row["capital"] + row["interes"] + row["iva"]
            if cancel_all or (amount >= total_row):
                if not cancel_all:
                    amount -= total_row
                liq = self.db.query(LiquidacionCuotaCedida).filter(LiquidacionCuotaCedida.id == i).first()
                if liq:
                    liq.fecha_pago = fecha_pago
                    liq.cancelada = True
                    cuotas_afectadas.add(liq.cuota_id)
                    cantidad_canceladas += 1
                df.loc[i, "cancelada"] = True
                df.loc[i, "fecha_pago"] = fecha_pago
            else:
                df.loc[i, "cancelada"] = False
                df.loc[i, "fecha_pago"] = None

        if cuotas_afectadas:
            cuotas_db = self.db.query(Cuota).filter(Cuota.id.in_(list(cuotas_afectadas))).all()
            for cuota in cuotas_db:
                cuota.actualizar_estado_cedido(fecha_pago)

        self.db.flush()
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error persisting the settlements transaction: {e}")

        sobrante = amount if not cancel_all else 0.0
        return df, sobrante, cantidad_canceladas

    def __del__(self):
        """
        Safely closes the database session if it was created internally.
        """
        if hasattr(self, "_own_session") and self._own_session and hasattr(self, "db") and self.db:
            self.db.close()
