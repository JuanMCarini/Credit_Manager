import pandas as pd

from str.collections.types import Identifier
from str.database.io import read_table


def installments(identifier: str | int, ident_type: Identifier) -> pd.DataFrame:
    df = read_table("installments", "ID")
    if ident_type in [Identifier.DNI, Identifier.CUIL]:
        df_clts = read_table("clients", ident_type._value_)
        id_client = df_clts.at[str(identifier), "ID"]
        df_crts = read_table("credits", "ID")
        id_credits = df_crts.loc[df_crts["Client_ID"] == id_client].index
        df = df.loc[df["Credit_ID"].isin(id_credits)]

    elif ident_type in [Identifier.ID_Credit, Identifier.ID_Original]:
        identifier = int(identifier)
        df = df.loc[df[ident_type._value_] == identifier]

    return df
