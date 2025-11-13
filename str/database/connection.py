# database/connection.py
import json
from typing import Literal

import pandas as pd
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
ENGINE = create_engine(connection_string)
BASE = declarative_base()

Tables = Literal[
    "business_partners",
    "purchases",
    "sales",
    "genders",
    "marital_status",
    "countries",
    "provinces",
    "cities",
    "clients",
    "employment_status",
    "additional_addresses",
    "phones",
    "credit_types",
    "business_lines",
    "organisms",
    "credits",
    "installments",
    "collection_types",
    "collections",
]


# --- Generic helpers --------------------------------------------------------
def read_table(table: Tables, index_col: str | None = None) -> pd.DataFrame:
    return pd.read_sql(table, ENGINE, index_col=index_col)


def write(df: pd.DataFrame, table: Tables) -> None:
    # Single choke point for persistence
    df.to_sql(table, ENGINE, index=False, if_exists="append")
