import pandas as pd
import src.imports.cql.read as read_files
from src.database import Cuota, EstadoCuota, SessionLocal, engine
from src.database import TipoCobranzaEnum, Cobranza


df_creditos = pd.read_sql("creditos", engine, index_col="id_externo")
df_cuotas = read_files.df_cuotas.copy()
df_inventario = read_files.df_inventario.copy()
df_cuotas = df_cuotas.merge(
    df_inventario[['Clave Externa']], 
    left_on="Crédito", 
    right_on="Id. Op.", 
    how="left"
)
df_cuotas["credito_id"] = df_cuotas['Clave Externa'].map(df_creditos["id"])

db = SessionLocal()

new_quotas = []
for i, row in df_cuotas.iterrows():
    new_quota = Cuota(
        credito_id=row["credito_id"],
        nro_cuota=row["Cuota"],
        fecha_vencimiento=row["Vto."],
        capital=row["CA"],
        interes=row["IN"],
        iva=row["IV"],
    )
    new_quotas.append(new_quota)

db.add_all(new_quotas)
db.commit()

df_cobranzas = read_files.df_cobranzas.copy()
mask = (
    (df_cobranzas["Tipo Cobranza"] == "ANTICIPO")
    & (df_cobranzas["Línea"] == "ANTICIPO")
)
df_cobranzas = df_cobranzas.loc[~mask]
df_cuotas = pd.read_sql("cuotas", engine, index_col="id")
df_cobranzas = df_cobranzas.merge(
    df_inventario[['Clave Externa']], 
    left_on="Crédito", 
    right_on="Id. Op.", 
    how="left"
)
df_cobranzas["credito_id"] = df_cobranzas["Clave Externa"].map(df_creditos["id"])
mask_null = (
    (df_cobranzas["credito_id"].isna())
    & (df_cobranzas["Línea"] == "PENALTY")
)
df_cobranzas = df_cobranzas.loc[~mask_null]
if not df_cobranzas[df_cobranzas["credito_id"].isna()].empty:
    from IPython.display import display
    display(df_cobranzas[df_cobranzas["credito_id"].isna()])
    raise ValueError("No se encontraron créditos")
else:
    df_cobranzas = df_cobranzas.loc[~df_cobranzas["credito_id"].isna()]
df_cobranzas["credito_id"] = df_cobranzas["credito_id"].astype(int)

# Detectamos el nombre de la columna del índice de df_cuotas (usualmente "id" o "index")
col_id = df_cuotas.index.name if df_cuotas.index.name else "index"
# Hacemos un merge left y nos quedamos con el ID de la cuota
df_cobranzas = df_cobranzas.merge(
    df_cuotas.reset_index()[[col_id, "credito_id", "nro_cuota"]],
    left_on=["credito_id", "Cta."],
    right_on=["credito_id", "nro_cuota"],
    how="left"
).rename(columns={col_id: "cuota_id"}).drop(columns=["nro_cuota"])

for col in ["CA", "IN", "IV", "TOTAL"]:
    df_cobranzas[col] = df_cobranzas[col].astype(float).abs()

tipos_cobranzas = {
    'ANTICIPO': TipoCobranzaEnum.ANTICIPO,
    'COBRANZA': TipoCobranzaEnum.COMUN,
    'COBRANZA X CANCEL ANT': TipoCobranzaEnum.BCA,
    'CUOTA NO COMPRADA': TipoCobranzaEnum.CNC,
    'RECIBO': TipoCobranzaEnum.AJUSTE
}

df_cobranzas["Tipo Cobranza"] = df_cobranzas["Tipo Cobranza"].map(tipos_cobranzas)
mask = df_cobranzas["Línea"] == "PENALTY"
df_cobranzas.loc[mask, "Tipo Cobranza"] = TipoCobranzaEnum.PENALTY
mask = (
    (df_cobranzas["Tipo Cobranza"] == TipoCobranzaEnum.COMUN)
    & (df_cobranzas["CA"] != 0)
    & (df_cobranzas["IN"] == 0)
    & (df_cobranzas["IV"] == 0)
    )

df_cobranzas.loc[mask, "Tipo Cobranza"] = TipoCobranzaEnum.CA

collections = []
for i, row in df_cobranzas.iterrows():
    new_coll = Cobranza(
        cuota_id=row["cuota_id"],
        tipo_cobranza=row["Tipo Cobranza"],
        capital=row["CA"],
        interes=row["IN"],
        iva=row["IV"],
        fecha=row["Emisión"]
    )
    collections.append(new_coll)

db.add_all(collections)
db.commit()
db.close()
