import json
import pandas as pd

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from str.database.connection import engine
from str.tool import _log


# Leer el contenido del archivo .sql
ruta_sql_structure = 'config/structure.sql'
with open(ruta_sql_structure, 'r') as file:
    sql_script = file.read()

# Intentar conectar al motor y ejecutar el script SQL
try:    
    with engine.connect() as connection:
        # Divide el script completo en sentencias individuales por línea
        statements = sql_script.split('\n')
        all_good = True
        # Ejecuta cada sentencia SQL, ignorando comentarios y líneas vacías
        for i, statement in enumerate(statements):
            statement = statement.strip()  # Elimina espacios en blanco
            if statement and not statement.startswith('--'):  # Ignora comentarios y vacíos
                try:
                    connection.execute(text(statement))
                    _log(f"{i}: {statement}", False)  # Imprime la sentencia ejecutada con su índice
                except SQLAlchemyError as e:
                    all_good = False
                    _log(f"❌ Error al ejecutar la sentencia {i}: {statement}")
                    _log(f"    Detalle del error: {e}")
                    
    if all_good:
        _log("\n✔️ Base de datos creada correctamente.\n")
    else:
        _log("🚨 No todas las sentencias del script se ejecutaron correctamente.")
        
    
except SQLAlchemyError as e:
    _log(f"🚨 Error al conectar con la base de datos o al ejecutar el script completo: {e}")
    
    # Crear DataFrame de los sexos
df_sexo = pd.DataFrame({
    'ID': [0, 1, 2, 3],
    'Description': ['No Binario','Masculino', 'Femenino', 'Otro']})
df_sexo.set_index('ID', inplace=True)
df_sexo.to_sql('gender', engine, if_exists='append', index=True)
_log("✔️ Tabla 'gender' actualizada correctamente.\n")

# Crear DataFrame de estado civil
df_estado_civil = pd.DataFrame({
    'ID': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    'Description': 
        ['Soltero', 'Casado C/Com de Bienes', 'Viudo', 'Divorciado', 'Separado', 'Conviviente C/Com de Bienes', 'Conviviente C/Sep de Bienes', 'Casado C/Sep de Bienes', 'En Tránsito', 'Desconocido']})
df_estado_civil.set_index('ID', inplace=True)
df_estado_civil.to_sql('marital_status', engine, if_exists='append', index=True)
_log("✔️ Tabla 'marital_status' actualizada correctamente.\n")


# Access the values
with open("config/owner.json", "r", encoding="utf-8") as file:
    company_data = json.load(file)
company = company_data["Company_Name"]
cuil    = company_data["CUIL"]
email   = company_data["Email"]

df_bp = pd.read_sql('business_partners', engine, index_col='ID')
df_bp.loc[0] = {'Company_Name': company, 'CUIL': cuil, 'Email': email}
df_bp.to_sql('business_partners', engine, index=True, if_exists='append')
_log(f"✔️ Sistema inicializado correctamente a nombre de {company}.\n")