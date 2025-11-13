# collections/io.py
from __future__ import annotations

from typing import Literal

import pandas as pd

from str.database.connection import engine

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
    "credit_type",
    "business_lines",
    "organisms",
    "credits",
    "installments",
    "collection_type",
    "collections",
]


# --- Generic helpers --------------------------------------------------------
def read_table(table: Tables, index_col: str | None = None) -> pd.DataFrame:
    return pd.read_sql(table, engine, index_col=index_col)


def write(df: pd.DataFrame, table: str) -> None:
    # Single choke point for persistence
    df.to_sql(table, engine, index=False, if_exists="append")
