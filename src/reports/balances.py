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
    for col in ["fecha_emision", "cliente_cuil", "cartera_id", "socio_originador_id", "tipo_credito", "estado"]:
        df_ctas[col] = df_ctas["credito_id"].map(df_crts[col])
    
    df_ctas["estado_credito"] = df_ctas["credito_id"].map(df_crts["estado"])
    
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
        columns=["Dueño_id_tmp", "Partner_Name", "comercializada"],
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
                "estado_credito",
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
        "estado_credito": "Estado Credito",
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

def cobranzas_recibidas(meses: int = 12, fecha: datetime | None = None):
    """
    =============================================================================
    Function: cobranzas_recibidas
    Description: Generates an optimized historical collections report.
                 Returns raw numeric DataFrames grouped by period, Owner and Originator.
    =============================================================================
    """
    if fecha is None:
        fecha = datetime.today()
        
    fecha_inicio = (fecha - pd.DateOffset(months=meses - 1)).replace(day=1)
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha.strftime("%Y-%m-%d")
    sql_params = {"fecha_inicio": fecha_inicio_str, "fecha_fin": fecha_fin_str}

    df_cobr = pd.read_sql_query(
        text("SELECT * FROM cobranzas WHERE fecha >= :fecha_inicio AND fecha <= :fecha_fin"),
        engine,
        params=sql_params,
        index_col="id",
    )

    if df_cobr.empty:
        return pd.DataFrame()

    df_ctas = pd.read_sql_query(text("SELECT * FROM cuotas"), engine, index_col="id")
    df_crts = pd.read_sql_query(text("SELECT * FROM creditos"), engine, index_col="id")
    df_cart = pd.read_sql("carteras", engine, index_col="id")
    df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")
    df_op_cart = pd.read_sql_query(text("SELECT * FROM operaciones_cartera"), engine, index_col="cuota_id")

    df_cobr["credito_id"] = df_cobr["cuota_id"].map(df_ctas["credito_id"])
    df_cobr["cartera_id"] = df_cobr["credito_id"].map(df_crts["cartera_id"])
    df_cobr["socio_originador_id"] = df_cobr["credito_id"].map(df_crts["socio_originador_id"])
    df_cobr["tipo_credito"] = df_cobr["credito_id"].map(df_crts["tipo_credito"])

    df_cobr["socio_id"] = df_cobr["cartera_id"].map(df_cart["socio_id"])
    df_cobr["Originador"] = df_cobr["socio_originador_id"].map(df_socios["razon_social"])

    mask_penalty = (
        (df_cobr["Originador"].isna())
        & (df_cobr["tipo_credito"] == "PENALTY"))
    df_cobr.loc[mask_penalty, "Originador"] = "PENALTY"

    df_op_cart = df_op_cart.sort_values(by="fecha_registro")
    df_op_cart = df_op_cart[~df_op_cart.index.duplicated(keep="last")]

    df_cobr["Dueño_id_tmp"] = df_cobr["cuota_id"].map(df_op_cart["cartera_id"])
    df_cobr["tipo_op"] = df_cobr["Dueño_id_tmp"].map(df_cart["tipo_operacion"])
    df_cobr["comercializada"] = df_cobr["cuota_id"].map(df_op_cart["cuota_comercializada"])
    df_cobr["Partner_Name"] = df_cobr["Dueño_id_tmp"].map(df_cart["socio_id"]).map(df_socios["razon_social"])

    company_data = get_company_data()

    conditions = [
        (df_cobr["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df_cobr["comercializada"] == True),
        (df_cobr["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df_cobr["comercializada"] == False),
        (df_cobr["tipo_op"] == "VENTA") & (df_cobr["comercializada"] == True),
        (df_cobr["tipo_op"] == "VENTA") & (df_cobr["comercializada"] == False),
    ]
    choices = [
        company_data.razon_social,
        df_cobr["Partner_Name"],
        df_cobr["Partner_Name"],
        company_data.razon_social,
    ]
    df_cobr["Dueño"] = np.select(conditions, choices, default=company_data.razon_social)
    
    df_cobr['periodo'] = pd.to_datetime(df_cobr['fecha']).dt.strftime('%Y-%m')
    
    # Calculate recupero_mora (payments made after the due date)
    df_cobr['fecha_vencimiento'] = pd.to_datetime(df_cobr['cuota_id'].map(df_ctas['fecha_vencimiento']))
    df_cobr['fecha_pago_dt'] = pd.to_datetime(df_cobr['fecha'])
    df_cobr['es_mora'] = df_cobr['fecha_pago_dt'] > df_cobr['fecha_vencimiento']
    df_cobr['recupero_mora'] = np.where(df_cobr['es_mora'], df_cobr['capital'] + df_cobr['interes'] + df_cobr['iva'], 0)

    agrupado = df_cobr.groupby(['periodo', 'Dueño', 'Originador', 'tipo_cobranza'], dropna=False)[['capital', 'interes', 'iva', 'recupero_mora']].sum().reset_index()
    
    agrupado['total'] = agrupado['capital'] + agrupado['interes'] + agrupado['iva']
    
    return agrupado

def cuotas_teoricas(meses: int = 12, fecha: datetime | None = None):
    if fecha is None:
        fecha = datetime.today()
        
    fecha_inicio = (fecha - pd.DateOffset(months=meses - 1)).replace(day=1)
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha.strftime("%Y-%m-%d")
    sql_params = {"fecha_inicio": fecha_inicio_str, "fecha_fin": fecha_fin_str}

    # Query only cuotas whose expiration falls in the window
    df_ctas = pd.read_sql_query(
        text("SELECT * FROM cuotas WHERE fecha_vencimiento >= :fecha_inicio AND fecha_vencimiento <= :fecha_fin"),
        engine,
        params=sql_params,
        index_col="id",
    )

    if df_ctas.empty:
        return pd.DataFrame()

    df_crts = pd.read_sql_query(text("SELECT * FROM creditos"), engine, index_col="id")
    df_cart = pd.read_sql("carteras", engine, index_col="id")
    df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")
    df_op_cart = pd.read_sql_query(text("SELECT * FROM operaciones_cartera"), engine, index_col="cuota_id")

    df_ctas["cartera_id"] = df_ctas["credito_id"].map(df_crts["cartera_id"])
    df_ctas["socio_originador_id"] = df_ctas["credito_id"].map(df_crts["socio_originador_id"])
    df_ctas["tipo_credito"] = df_ctas["credito_id"].map(df_crts["tipo_credito"])

    df_ctas["Originador"] = df_ctas["socio_originador_id"].map(df_socios["razon_social"])

    mask_penalty = (
        (df_ctas["Originador"].isna())
        & (df_ctas["tipo_credito"] == "PENALTY"))
    df_ctas.loc[mask_penalty, "Originador"] = "PENALTY"

    df_op_cart = df_op_cart.sort_values(by="fecha_registro")
    df_op_cart = df_op_cart[~df_op_cart.index.duplicated(keep="last")]

    df_ctas["Dueño_id_tmp"] = df_ctas.index.map(df_op_cart["cartera_id"])
    df_ctas["tipo_op"] = df_ctas["Dueño_id_tmp"].map(df_cart["tipo_operacion"])
    df_ctas["comercializada"] = df_ctas.index.map(df_op_cart["cuota_comercializada"])
    df_ctas["Partner_Name"] = df_ctas["Dueño_id_tmp"].map(df_cart["socio_id"]).map(df_socios["razon_social"])

    company_data = get_company_data()

    conditions = [
        (df_ctas["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df_ctas["comercializada"] == True),
        (df_ctas["tipo_op"].isin(["COMPRA", "RECOMPRA"])) & (df_ctas["comercializada"] == False),
        (df_ctas["tipo_op"] == "VENTA") & (df_ctas["comercializada"] == True),
        (df_ctas["tipo_op"] == "VENTA") & (df_ctas["comercializada"] == False),
    ]
    choices = [
        company_data.razon_social,
        df_ctas["Partner_Name"],
        df_ctas["Partner_Name"],
        company_data.razon_social,
    ]
    df_ctas["Dueño"] = np.select(conditions, choices, default=company_data.razon_social)
    
    df_ctas['periodo'] = pd.to_datetime(df_ctas['fecha_vencimiento']).dt.strftime('%Y-%m')

    # Calculate real collections for these specific cuotas, up to fecha_corte (fecha_fin)
    df_cobr_teo = pd.read_sql_query(
        text("SELECT cuota_id, capital, interes, iva FROM cobranzas WHERE fecha <= :fecha_fin"),
        engine,
        params={"fecha_fin": fecha_fin_str}
    )
    if not df_cobr_teo.empty:
        cobr_grouped = df_cobr_teo.groupby('cuota_id')[['capital', 'interes', 'iva']].sum()
        df_ctas['cobr_capital'] = df_ctas.index.map(cobr_grouped['capital']).fillna(0)
        df_ctas['cobr_interes'] = df_ctas.index.map(cobr_grouped['interes']).fillna(0)
        df_ctas['cobr_iva'] = df_ctas.index.map(cobr_grouped['iva']).fillna(0)
    else:
        df_ctas['cobr_capital'] = 0
        df_ctas['cobr_interes'] = 0
        df_ctas['cobr_iva'] = 0

    agrupado = df_ctas.groupby(['periodo', 'Dueño', 'Originador'], dropna=False)[
        ['capital', 'interes', 'iva', 'cobr_capital', 'cobr_interes', 'cobr_iva']
    ].sum().reset_index()
    
    agrupado['total'] = agrupado['capital'] + agrupado['interes'] + agrupado['iva']
    agrupado['total_cobr'] = agrupado['cobr_capital'] + agrupado['cobr_interes'] + agrupado['cobr_iva']
    
    return agrupado
