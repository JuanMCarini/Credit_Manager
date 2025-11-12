from typing import Any

import pandas as pd

from str.database.connection import engine


def id(value: Any, table_name: str) -> int:
    """
    Acepta:
      - valor de la variable
      - table_name nombre de la tabla
    Devuelve el ID de la base (según el value y la tabla).
    """
    if table_name is None:
        raise ValueError(f"Falta {table_name}.")
    s = str(value).strip().upper()
    df = pd.read_sql(table_name, engine, index_col="ID")
    if s in df["Description"].values:
        return int(df.index[df["Description"] == s][0])
    else:
        raise ValueError(
            f'"{s}" no está en la tabla {table_name}: {df["Description"].values}.'
        )
