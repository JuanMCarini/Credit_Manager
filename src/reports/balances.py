"""
Module: balances.py
Description: Optimized financial reporting for Web API integration.
             Returns raw numerical data to allow frontend-side formatting.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.config import get_company_data
from src.database import engine


def saldos(
    fecha: datetime | None = None,
    con_saldo: bool = True,
    propias: bool | None = None,
    agrupar: bool = False,
    agrupadores: list[str] | None = None,
):
    """
    =============================================================================
    Function: saldos
    Description: Generates an optimized loan balance report.
                 Returns raw numeric DataFrames for API compatibility.
    =============================================================================
    """
    
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha)
    elif fecha is None:
        fecha = datetime.today()

    fecha_str = fecha.strftime("%Y-%m-%d")
    sql_params = {"fecha": fecha_str}

    # 1. SQL Push-down filtering
    df_crts = pd.read_sql_query(
        text("SELECT * FROM creditos WHERE fecha_emision <= :fecha"),
        engine,
        params=sql_params,
        index_col="id",
    )

    ctas_query = text("""
        SELECT c.* FROM cuotas c 
        JOIN creditos cr ON c.credito_id = cr.id 
        WHERE cr.fecha_emision <= :fecha
    """)

    df_ctas = pd.read_sql_query(ctas_query, engine, params=sql_params, index_col="id")
    df_cart = pd.read_sql("carteras", engine, index_col="id")
    df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")

    df_cobr = pd.read_sql_query(
        text("SELECT * FROM cobranzas WHERE fecha <= :fecha"),
        engine,
        params=sql_params,
        index_col="id",
    )
    df_op_cart = pd.read_sql_query(
        text("SELECT * FROM operaciones_cartera WHERE fecha_registro <= :fecha"),
        engine,
        params=sql_params,
        index_col="cuota_id",
    )

    # 2. Data Mapping
    for col in ["fecha_emision", "cliente_cuil", "cartera_id", "socio_originador_id", "tipo_credito"]:
        df_ctas[col] = df_ctas["credito_id"].map(df_crts[col])
    
    df_ctas["socio_id"] = df_ctas["cartera_id"].map(df_cart["socio_id"])
    df_ctas["Proveedor"] = df_ctas["socio_id"].map(df_socios["razon_social"])
    df_ctas["Originador"] = df_ctas["socio_originador_id"].map(
        df_socios["razon_social"]
    )
    df_ctas["recurso"] = df_ctas["cartera_id"].map(df_cart["recurso"])
    df_ctas["iva_operado"] = df_ctas["cartera_id"].map(df_cart["iva"])

    mask_penalty = (
        (df_ctas["Originador"].isna())
        & (df_ctas["tipo_credito"] == "PENALTY"))
    df_ctas.loc[mask_penalty, "Originador"] = "PENALTY"

    # 3. Financial Calculations
    df_cobr_sum = df_cobr.groupby("cuota_id")[["capital", "interes", "iva"]].sum()
    df = df_ctas.merge(
        df_cobr_sum,
        left_index=True,
        right_index=True,
        how="left",
        suffixes=("", "_cobr"),
    ).fillna(0.0)

    for col in ["capital", "interes", "iva"]:
        df[col] = (df[col].round(2) - df[f"{col}_cobr"].round(2)).round(2)

    df["total"] = df[["capital", "interes", "iva"]].sum(axis=1)

    if con_saldo:
        df = df[df["total"].round(2) != 0.0]

    # 4. Vectorized Ownership Logic
    df_op_cart = df_op_cart.sort_values(by="fecha_registro")
    df_op_cart = df_op_cart[~df_op_cart.index.duplicated(keep="last")]

    df["Dueño_id_tmp"] = df.index.map(df_op_cart["cartera_id"])
    df["tipo_op"] = df["Dueño_id_tmp"].map(df_cart["tipo_operacion"])
    df["comercializada"] = df.index.map(df_op_cart["cuota_comercializada"])
    df["Partner_Name"] = (
        df["Dueño_id_tmp"].map(df_cart["socio_id"]).map(df_socios["razon_social"])
    )
    company_data = get_company_data()

    conditions = [
        (df["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df["comercializada"] == True),  # noqa: E712
        (df["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df["comercializada"] == False),  # noqa: E712
        (df["tipo_op"] == "VENTA") & (df["comercializada"] == True),  # noqa: E712
        (df["tipo_op"] == "VENTA") & (df["comercializada"] == False),  # noqa: E712
    ]
    choices = [
        company_data.razon_social,
        df["Partner_Name"],
        df["Partner_Name"],
        company_data.razon_social,
    ]
    df["Dueño"] = np.select(conditions, choices, default=company_data.razon_social)

    df.drop(
        columns=["Dueño_id_tmp", "Partner_Name", "tipo_op", "comercializada"],
        inplace=True,
        errors="ignore",
    )

    if propias is None:
        pass
    elif propias:
        df = df[df["Dueño"] == company_data.razon_social]
    else:
        df = df[df["Dueño"] != company_data.razon_social]

    if agrupar and agrupadores:
        mapper = {
            "credito": "credito_id",
            "clientes": "cliente_cuil",
            "socios": "Proveedor",
            "carteras": "cartera_id",
            "originador": "Originador",
            "dueno": "Dueño",
            "dueño": "Dueño",
            "vencimientos": "fecha_vencimiento",
            "recurso": "recurso",
            "iva": "iva_operado"
        }
        lista_agrupadores = [mapper[g] for g in agrupadores if g in mapper]

        # We perform the sum but skip the string formatting
        df = df.groupby(lista_agrupadores, dropna=False)[["capital", "interes", "iva", "total"]].sum()
    else:
        df.reset_index(drop=False, inplace=True)
        df.set_index(["credito_id", "nro_cuota"], inplace=True)
        df = df[
            [
                "Proveedor",
                "cartera_id",
                "Originador",
                "cliente_cuil",
                "fecha_emision",
                "id",
                "fecha_vencimiento",
                "Dueño",
                "estado",
                "capital",
                "interes",
                "iva",
                "total",
                "capital_cobr",
                "interes_cobr",
                "iva_cobr",
            ]
        ]

    # 6. Standard Renaming
    renames = {
        "id": "ID Cuota",
        "credito_id": "ID Credito",
        "nro_cuota": "Nro. Cuota",
        "fecha_vencimiento": "Fecha Vencimiento",
        "estado": "Estado",
        "capital": "Capital",
        "interes": "Interés",
        "iva": "IVA",
        "total": "Total",
        "capital_cobr": "Capital Cobrado",
        "interes_cobr": "Interés Cobrado",
        "iva_cobr": "IVA Cobrado",
        "fecha_emision": "Fecha Emisión",
        "cliente_cuil": "CUIL Cliente",
        "cartera_id": "ID Cartera",
    }
    df.rename(columns=renames, errors="ignore", inplace=True)

    for col in ["ID Cartera", "Proveedor", "Originador"]:
        if col in df.columns:
            df[col] = df[col].replace(0.0, None)

    for col in ["Fecha Vencimiento", "Fecha Emisión"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    df.rename_axis(index=renames, inplace=True)

    return df
