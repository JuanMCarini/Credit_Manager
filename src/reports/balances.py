"""
Module: balances.py
Description: Optimized financial reporting for Web API integration.
             Returns raw numerical data to allow frontend-side formatting.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.config import COMPANY_DATA
from src.database import engine


def saldos(
    fecha: datetime | None = None,
    con_saldo: bool = True,
    propias: bool = True,
    agrupar: bool = False,
    clientes: bool = False,
    carteras: bool = False,
    socios: bool = False,
    originador: bool = False,
    vencimientos: bool = False,
    dueño: bool = False,
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
    for col in ["fecha_emision", "cliente_cuil", "cartera_id", "socio_originador_id"]:
        df_ctas[col] = df_ctas["credito_id"].map(df_crts[col])

    df_ctas["socio_id"] = df_ctas["cartera_id"].map(df_cart["socio_id"])
    df_ctas["Proveedor"] = df_ctas["socio_id"].map(df_socios["razon_social"])
    df_ctas["Originador"] = df_ctas["socio_originador_id"].map(
        df_socios["razon_social"]
    )

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
        df[col] -= df[f"{col}_cobr"]

    df.drop(columns=["capital_cobr", "interes_cobr", "iva_cobr"], inplace=True)
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

    conditions = [
        (df["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df["comercializada"] == True),
        (df["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df["comercializada"] == False),
        (df["tipo_op"] == "VENTA") & (df["comercializada"] == True),
        (df["tipo_op"] == "VENTA") & (df["comercializada"] == False),
    ]
    choices = [
        COMPANY_DATA.razon_social,
        df["Partner_Name"],
        df["Partner_Name"],
        COMPANY_DATA.razon_social,
    ]
    df["Dueño"] = np.select(conditions, choices, default=COMPANY_DATA.razon_social)

    df.drop(
        columns=["Dueño_id_tmp", "Partner_Name", "tipo_op", "comercializada"],
        inplace=True,
        errors="ignore",
    )

    if propias:
        df = df[df["Dueño"] == COMPANY_DATA.razon_social]

    # 5. Dynamic Grouping (Returning raw numbers)
    if agrupar and (
        clientes or socios or carteras or originador or vencimientos or dueño
    ):
        lista_agrupadores = []
        if clientes:
            lista_agrupadores.append("cliente_cuil")
        if socios:
            lista_agrupadores.append("Proveedor")
        if carteras:
            lista_agrupadores.append("cartera_id")
        if originador:
            lista_agrupadores.append("Originador")
        if dueño:
            lista_agrupadores.append("Dueño")
        if vencimientos:
            lista_agrupadores.append("fecha_vencimiento")

        # We perform the sum but skip the string formatting
        df = df.groupby(lista_agrupadores)[["capital", "interes", "iva", "total"]].sum()
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
                "capital",
                "interes",
                "iva",
                "total",
            ]
        ]

    # 6. Standard Renaming
    renames = {
        "id": "ID Cuota",
        "credito_id": "ID Credito",
        "nro_cuota": "Nro. Cuota",
        "fecha_vencimiento": "Fecha Vencimiento",
        "capital": "Capital",
        "interes": "Interés",
        "iva": "IVA",
        "fecha_emision": "Fecha Emisión",
        "cliente_cuil": "CUIL Cliente",
        "total": "Total",
        "cartera_id": "ID Cartera",
    }
    df.rename(columns=renames, errors="ignore", inplace=True)
    df.rename_axis(index=renames, inplace=True)

    return df
