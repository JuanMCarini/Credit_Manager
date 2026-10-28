import pandas as pd
from datetime import date
from src.database import SessionLocal
from src.database.models import Cartera, OperacionCartera, Cuota, TipoOperacionCartera


def get_df() -> pd.DataFrame:
    with SessionLocal() as db:
        query = (
            db.query(
                Cartera.nombre.label("cartera"),
                Cartera.estado.label("estado_cartera"),
                Cartera.tna_descuento,
                Cartera.fecha_compra,
                (Cuota.capital + Cuota.interes).label("importe_nominal"),
                Cuota.fecha_vencimiento,
            )
            .join(OperacionCartera, Cartera.id == OperacionCartera.cartera_id)
            .join(Cuota, OperacionCartera.cuota_id == Cuota.id)
            .filter(Cartera.tipo_operacion == TipoOperacionCartera.VENTA)
        )
        df = pd.read_sql(query.statement, db.get_bind())

    if not df.empty and "estado_cartera" in df.columns:
        df["estado_cartera"] = df["estado_cartera"].apply(
            lambda x: x.value if hasattr(x, "value") else str(x)
        )

    df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"])
    df["fecha_compra"] = pd.to_datetime(df["fecha_compra"])

    df["dias_al_vto"] = (df["fecha_vencimiento"] - df["fecha_compra"]).dt.days
    df["dias_al_vto"] = df["dias_al_vto"].clip(lower=0)

    df["tna_decimal"] = df["tna_descuento"].astype(float)
    if not df.empty and df["tna_decimal"].mean() > 1.5:
        df["tna_decimal"] = df["tna_decimal"] / 100

    df["importe_nominal"] = df["importe_nominal"].astype(float)
    df["valor_actual"] = df["importe_nominal"] / (
        (1 + (df["tna_decimal"] * 30 / 365)) ** (df["dias_al_vto"] / 30)
    )
    return df


def get_resumen() -> pd.DataFrame:
    df = get_df()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "estado_cartera",
                "fecha_compra",
                "tna_descuento",
                "cantidad_cuotas",
                "valor_nominal_total",
                "valor_actual_total",
                "diferencia_descuento",
            ],
            index=pd.Index([], name="cartera"),
        )
    resumen_df = (
        df.groupby(["cartera", "estado_cartera"])
        .agg(
            fecha_compra=("fecha_compra", "max"),
            tna_descuento=("tna_descuento", "max"),
            cantidad_cuotas=("importe_nominal", "count"),
            valor_nominal_total=("importe_nominal", "sum"),
            valor_actual_total=("valor_actual", "sum"),
        )
        .reset_index()
    )
    resumen_df["diferencia_descuento"] = (
        resumen_df["valor_nominal_total"] - resumen_df["valor_actual_total"]
    )
    return resumen_df.set_index("cartera")


def __getattr__(name: str):
    if name == "df":
        return get_df()
    if name == "resumen":
        return get_resumen()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
