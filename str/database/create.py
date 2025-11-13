import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from str.database.connection import engine
from str.tool import _log

# Leer el contenido del archivo .sql
ruta_sql_structure = "config/structure.sql"
with open(ruta_sql_structure, "r") as file:
    sql_script = file.read()

# Intentar conectar al motor y ejecutar el script SQL
try:
    with engine.connect() as connection:
        # Divide el script completo en sentencias individuales por línea
        statements = sql_script.split("\n")
        all_good = True
        # Ejecuta cada sentencia SQL, ignorando comentarios y líneas vacías
        for i, statement in enumerate(statements):
            statement = statement.strip()  # Elimina espacios en blanco
            if statement and not statement.startswith(
                "--"
            ):  # Ignora comentarios y vacíos
                try:
                    connection.execute(text(statement))
                    _log(
                        f"{i}: {statement}", False
                    )  # Imprime la sentencia ejecutada con su índice
                except SQLAlchemyError as e:
                    all_good = False
                    _log(f"❌ Error al ejecutar la sentencia {i}: {statement}")
                    _log(f"    Detalle del error: {e}")

    if all_good:
        _log("\n✔️ Base de datos creada correctamente.\n")
    else:
        _log("🚨 No todas las sentencias del script se ejecutaron correctamente.")


except SQLAlchemyError as e:
    _log(
        f"🚨 Error al conectar con la base de datos o al ejecutar el script completo: {e}"
    )

# Crear DataFrame de los sexos
genders = ["No Binario", "Masculino", "Femenino", "Otro"]
genders = [str(gender).upper() for gender in genders]
df_sexo = pd.DataFrame(genders, columns=["Description"])
df_sexo.to_sql("genders", engine, if_exists="append", index=False)
_log("✔️ Tabla 'genders' actualizada correctamente.\n")

# Crear DataFrame de estado civil
marital_statuses = [
    "Soltero/a",
    "Casado/a",
    "Viudo/a",
    "Divorciado/a",
    "Conviviente",
    "Desconocido",
]
marital_statuses_upper = [s.upper() for s in marital_statuses]
df_estado_civil = pd.DataFrame(
    marital_statuses_upper,
    columns=["Description"],
)
df_estado_civil.to_sql("marital_status", engine, if_exists="append", index=False)
_log("✔️ Tabla 'marital_status' actualizada correctamente.\n")

# Crear DataFrame de tipos de créditos
pd.DataFrame(["FRANCES", "ALEMAN", "PENALTY"], columns=["Name"]).to_sql(
    "credit_types", engine, index=False, if_exists="append"
)
Credit_Types = pd.read_sql("credit_types", engine, index_col="Name").sort_values(
    by="ID"
)
_log("✔️ Tabla 'credit_types' actualizada correctamente.\n")

# Crear DataFrame de tipos de cobranzas
pd.DataFrame(
    ["COMUN", "ANTICIPADA", "BONIFICACION", "PENALTY"], columns=["Type"]
).to_sql("collection_types", engine, index=False, if_exists="append")
Collection_Types = pd.read_sql(
    "collection_types", engine, index_col="Type"
).sort_values(by="ID")
_log("✔️ Tabla 'collection_types' actualizada correctamente.\n")

# Access the values
with open("config/owner.json", "r", encoding="utf-8") as file:
    company_data = json.load(file)
company = company_data["Company_Name"]
cuil = company_data["CUIL"]
email = company_data["Email"]

df_bp = pd.read_sql("business_partners", engine, index_col="ID")
df_bp.loc[0] = {"Name": company, "CUIT": cuil, "Email": email, "Active": True}
df_bp.to_sql("business_partners", engine, index=True, if_exists="append")
_log(f"✔️ Sistema inicializado correctamente a nombre de {company}.\n")

OUR_COMPANY_ID = int(
    pd.read_sql("business_partners", engine, index_col="ID").index.max()
)
