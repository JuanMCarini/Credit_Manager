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
    "employer",
    "employers_clients",
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
def read_table(table: Tables | str, index_col: str | None = "ID") -> pd.DataFrame:
    """
    Read a SQL table into a pandas DataFrame and normalize its dtypes:
      - Datetime columns are converted to Period[D]
      - Empty columns receive a consistent default dtype
      - ID/DNI/CUIL columns are cast to nullable integer (Int64)
      - Boolean-like columns are converted to boolean (nullable)
    """

    df = pd.read_sql(table, ENGINE)

    for col in df.columns:
        s = df[col]
        name = col.lower()

        # 1) Datetime → Period[D]
        if pd.api.types.is_datetime64_any_dtype(s):
            df[col] = s.dt.to_period("D")
            continue

        # 2) Completely empty column: assign a consistent dtype
        if s.count() == 0:  # all NaN
            if col.endswith("ID") or name in {"dni", "cuil", "cuit"}:
                df[col] = s.astype("Int64")  # nullable integer

            elif "name" in name or "address" in name or "email" in name:
                df[col] = s.astype("object")

            elif "date" in name:
                # empty date column → Period[D]
                df[col] = pd.PeriodIndex([], freq="D")

            elif name in {"active", "is_active"} or name.startswith("is_"):
                # empty boolean column → boolean (nullable)
                df[col] = s.astype("boolean")

            # if no rule matches, keep SQL dtype
            continue

        # 3) If column is an ID, DNI, or CUIL → cast to nullable integer
        if col.endswith("ID") or name in {"dni", "cuil", "cuit"}:
            df[col] = s.astype("Int64")
            continue

        # 4) Already-boolean columns → leave unchanged
        if pd.api.types.is_bool_dtype(s) or str(s.dtype) == "boolean":
            continue

        # 5) Integer columns containing only 0/1 → convert to boolean (nullable)
        if pd.api.types.is_integer_dtype(s) and set(s.dropna().unique()) <= {0, 1}:
            df[col] = s.astype("boolean")
            continue

        # 6) Object columns that look boolean → convert to boolean (nullable)
        if pd.api.types.is_object_dtype(s):
            vals = {str(v).strip().lower() for v in s.dropna().unique()}
            if vals <= {"0", "1", "true", "false"}:
                df[col] = (
                    s.astype(str)
                    .str.strip()
                    .str.lower()
                    .map({"1": True, "true": True, "0": False, "false": False})
                    .astype("boolean")
                )
                continue

    df.set_index(index_col, inplace=True)
    df = df.sort_index()
    return df


def write_table(df: pd.DataFrame, table: Tables | str) -> None:
    # Single choke point for persistence
    df.to_sql(table, ENGINE, index=False, if_exists="append")
