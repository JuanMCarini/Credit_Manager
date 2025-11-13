import pandas as pd

import str.collections.search as search
from str.collections.types import MONEY_COLS, Identifier
from str.database.io import read_table


def balances(identifier: str | int, ident_type: Identifier) -> pd.DataFrame:
    df_inst = search.installments(identifier, ident_type)
    df_coll = read_table("collections", "ID")
    df_coll = df_coll.loc[df_coll["Installment_ID"].isin(df_inst.index)]
    df_coll = df_coll.groupby(["Installment_ID"])[MONEY_COLS].sum().astype(float)
    df_sdos = df_inst.merge(
        df_coll,
        how="left",
        left_index=True,
        right_on="Installment_ID",
        suffixes=["", "_coll"],
    )
    for col in MONEY_COLS:
        df_sdos[f"{col}_coll"] = df_sdos[f"{col}_coll"].fillna(0.0)
        df_sdos[col] = df_sdos[col] - df_sdos[f"{col}_coll"]
        df_sdos.drop(columns=[f"{col}_coll"], inplace=True)
        # df_sdos.sort_values(by=["Due_Date", "Credit_ID", "Inst_Num"], inplace=True)

    df_sdos["Due_Date"] = df_sdos["Due_Date"].dt.to_period("D")
    df_sdos.reset_index(inplace=True)

    return df_sdos
