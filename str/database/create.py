# database/create.py.py
import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from str.categories import COLLECTION_TYPES, CREDIT_TYPES, GENDERS, MARITAL_STATUS
from str.database.connection import ENGINE, read_table, write_table
from str.database.structure import City, Country, Province
from str.tool import _log, log

# Leer el contenido del archivo .sql
ruta_sql_structure = "config/structure.sql"
with open(ruta_sql_structure, "r") as file:
    sql_script = file.read()

# Intentar conectar al motor y ejecutar el script SQL
try:
    with ENGINE.connect() as connection:
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
        _log("\n✔️ Base de datos creada correctamente.\n", log)
    else:
        _log("🚨 No todas las sentencias del script se ejecutaron correctamente.")


except SQLAlchemyError as e:
    _log(
        f"🚨 Error al conectar con la base de datos o al ejecutar el script completo: {e}"
    )

# Crear DataFrame de los sexos
df_sexo = pd.DataFrame(GENDERS, columns=["Description"])
write_table(df_sexo, "genders")
_log("✔️ Tabla 'genders' actualizada correctamente.\n", log)

# Crear DataFrame de estado civil
df_estado_civil = pd.DataFrame(MARITAL_STATUS, columns=["Description"])
write_table(df_estado_civil, "marital_status")
_log("✔️ Tabla 'marital_status' actualizada correctamente.\n", log)

# Crear DataFrame de tipos de créditos
df_ct = pd.DataFrame(CREDIT_TYPES, columns=["Name"])
write_table(df_ct, "credit_types")
_log("✔️ Tabla 'credit_types' actualizada correctamente.\n", log)

# Crear DataFrame de tipos de cobranzas
df_coll = pd.DataFrame(COLLECTION_TYPES, columns=["Type"])
write_table(df_coll, "collection_types")
Collection_Types = read_table("collection_types", "Type").sort_values(by="ID")
_log("✔️ Tabla 'collection_types' actualizada correctamente.\n", log)

# Agregar países
arg = Country("Argentina", "ARGENTINA/O")
arg = Country("Brasil", "Brasilero/a")
# Agregar una provincia
prov = Province("Buenos Aires", "Argentina")
# Agregar una ciudad
city = City("Bahía Blanca", "Buenos Aires", "Argentina")

# Access the values
with open("config/owner.json", "r", encoding="utf-8") as file:
    company_data = json.load(file)
company = company_data["Company_Name"]
cuil = company_data["CUIL"]
email = company_data["Email"]

df_bp = read_table("business_partners", "ID")
df_bp.loc[0] = {"Name": company, "CUIT": cuil, "Email": email, "Active": True}
write_table(df_bp, "business_partners")
_log(f"✔️ Sistema inicializado correctamente a nombre de {company}.\n", log)

OUR_COMPANY_ID = int(read_table("business_partners", "ID").index.max())
