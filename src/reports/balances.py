"""
Module: balances.py
Description: Financial reporting and analytics for the Credit Manager system.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text

# Import the global company configuration
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
                 Offloads initial filtering to the SQL engine to minimize memory
                 usage and improves performance on large datasets.
    Author: Juan Martín Carini
    Date: 2026-05-14
    Location: Bahía Blanca, Argentina
    =============================================================================
    """
    if fecha is None:
        fecha = datetime.today()

    # Formatting date for SQL parameter injection
    fecha_str = fecha.strftime("%Y-%m-%d")
    sql_params = {"fecha": fecha_str}

    # 1. Database extraction using optimized SQL queries (Push-down filtering)
    # We only retrieve credits and related records emitted or registered before the cut-off date
    df_crts = pd.read_sql_query(
        text("SELECT * FROM creditos WHERE fecha_emision <= :fecha"),
        engine,
        params=sql_params,
        index_col="id",
    )

    # We only need installments for the credits filtered above to avoid full table scans
    ctas_query = text("""
        SELECT c.* FROM cuotas c 
        JOIN creditos cr ON c.credito_id = cr.id 
        WHERE cr.fecha_emision <= :fecha
    """)
    df_ctas = pd.read_sql_query(ctas_query, engine, params=sql_params, index_col="id")

    # Static or smaller tables can still be read fully or mapped
    df_cart = pd.read_sql("carteras", engine, index_col="id")
    df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")

    # Transactional tables filtered at the source
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

    # 2. Map hierarchical attributes to the installments dataframe
    for col in ["fecha_emision", "cliente_cuil", "cartera_id", "socio_originador_id"]:
        df_ctas[col] = df_ctas["credito_id"].map(df_crts[col])

    df_ctas["socio_id"] = df_ctas["cartera_id"].map(df_cart["socio_id"])

    # Map Business Names for vendors and originators
    df_ctas["Proveedor"] = df_ctas["socio_id"].map(df_socios["razon_social"])
    df_ctas["Originador"] = df_ctas["socio_originador_id"].map(
        df_socios["razon_social"]
    )

    # 3. Process and summarize collections
    df_cobr_sum = df_cobr.groupby("cuota_id")[["capital", "interes", "iva"]].sum()

    # 4. Merge expected installments with actual collections
    df = df_ctas.merge(
        df_cobr_sum,
        left_index=True,
        right_index=True,
        how="left",
        suffixes=("", "_cobr"),
    )
    df = df.fillna(0.0)

    # 5. Calculate outstanding balance
    for col in ["capital", "interes", "iva"]:
        df[col] -= df[f"{col}_cobr"]

    df.drop(columns=["capital_cobr", "interes_cobr", "iva_cobr"], inplace=True)
    df["total"] = df[["capital", "interes", "iva"]].sum(axis=1)

    # Discard fully paid installments if requested
    if con_saldo:
        df = df[df["total"].round(2) != 0.0]

    # 6. Ownership logic determination (Vectorized with np.select)
    # Ensure chronological order and take the latest transaction status
    df_op_cart = df_op_cart.sort_values(by="fecha_registro")
    df_op_cart = df_op_cart[~df_op_cart.index.duplicated(keep="last")]

    # Temporary mapping for ownership calculation
    df["Dueño_id_tmp"] = df.index.map(df_op_cart["cartera_id"])
    df["tipo_operacion"] = df["Dueño_id_tmp"].map(df_cart["tipo_operacion"])
    df["cuota_comercializada"] = df.index.map(df_op_cart["cuota_comercializada"])

    # Map the partner name from the portfolio socio_id
    df["Partner_Name"] = (
        df["Dueño_id_tmp"].map(df_cart["socio_id"]).map(df_socios["razon_social"])
    )

    # Define boolean masks for np.select
    conditions = [
        (df["tipo_operacion"].isin(["COMPRA", "RECOMPRA"]))
        & (df["cuota_comercializada"] == True),  # noqa: E712
        (df["tipo_operacion"].isin(["COMPRA", "RECOMPRA"]))
        & (df["cuota_comercializada"] == False),  # noqa: E712
        (df["tipo_operacion"] == "VENTA") & (df["cuota_comercializada"] == True),  # noqa: E712
        (df["tipo_operacion"] == "VENTA") & (df["cuota_comercializada"] == False),  # noqa: E712
    ]

    # Ownership targets per condition
    choices = [
        COMPANY_DATA.razon_social,  # Repurchased or internal management
        df["Partner_Name"],  # Currently owned by the buying partner
        df["Partner_Name"],  # Currently owned by the partner (sold)
        COMPANY_DATA.razon_social,  # Transaction not effective or reverted
    ]

    # Assign final ownership, defaulting to the company for self-originated credits
    df["Dueño"] = np.select(conditions, choices, default=COMPANY_DATA.razon_social)

    # Cleanup temporary calculation columns
    df.drop(
        columns=[
            "Dueño_id_tmp",
            "Partner_Name",
            "tipo_operacion",
            "cuota_comercializada",
        ],
        inplace=True,
        errors="ignore",
    )

    if propias:
        df = df[df["Dueño"] == COMPANY_DATA.razon_social]

    # 7. Dynamic data grouping
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

        df = (
            df.groupby(lista_agrupadores)[["capital", "interes", "iva", "total"]]
            .sum()
            .map("$ {:,.2f}".format)
        )
    else:
        df.reset_index(drop=False, inplace=True)
        df.set_index(["credito_id", "nro_cuota"], inplace=True)
        # Final column selection
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

    # 8. Renaming and indexing standardization
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
