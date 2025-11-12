import json

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

# Load data from the config.json file
with open("config/config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

# Access the values
user = config["user"]
password = config["password"]
host = config["host"]
database = config["database"]

# Crea la cadena de conexión
connection_string = f"mysql+pymysql://{user}:{password}@{host}/{database}"

# Crear un motor SQLAlchemy
engine = create_engine(connection_string)
base = declarative_base()
