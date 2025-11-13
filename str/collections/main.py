import pandas as pd

from str.collections.balances import balances
from str.database.connection import engine
from str.database.structure import (
    OUR_COMPANY_ID,
    CollectionType,
    Credit,
    CreditType,
    Identifier,
)


def process(
    identifier: str | int,
    ident_type: Identifier,
    type: CollectionType,
    amount: float,
    date: str | pd.Period = pd.Period.now("D"),
) -> pd.DataFrame:
    df_sdos = balances(identifier, ident_type)

    date = pd.Period(date, freq="D")
    if type == CollectionType.COMUN:
        df_sdos["Total_CumSum"] = df_sdos["Total"].cumsum()
    elif type == CollectionType.ANTICIPADA:
        for col in ["Interest", "IVA"]:
            df_sdos.loc[df_sdos["Due_Date"] > date, col] = 0.0
        df_sdos["Total"] = df_sdos[["Capital", "Interest", "IVA"]].sum(axis=1)
        df_sdos["Total_CumSum"] = df_sdos["Total"].cumsum()
    df_sdos.reset_index(inplace=True)

    total_deuda = df_sdos["Total"].sum()
    if total_deuda < amount:
        penalty = amount - total_deuda
        df_crts = pd.read_sql("credits", engine, index_col="ID")
        client_id = df_crts.loc[
            df_crts.index.isin(df_sdos["Credit_ID"]), "Client_ID"
        ].unique()[0]
        org_id = df_crts.loc[
            df_crts.index.isin(df_sdos["Credit_ID"]), "Organism_ID"
        ].unique()[0]
        new_penalty = Credit(
            None,
            0.0,
            penalty,
            CreditType.PENALTY,
            0.0,
            1,
            client_id,
            org_id,
            date,
            0,
            date.day,
        )
        penalty_id = df_sdos.index.max() + 1
        df_sdos.loc[penalty_id] = {
            "Credit_ID": new_penalty,
            "Inst_Num": 1,
            "Owner_ID": OUR_COMPANY_ID,
            "Due_Date": new_penalty.First_Due_Date,
            "Capital": new_penalty.Capital,
            "Interest": penalty / 1.21,
            "IVA": penalty - penalty / 1.21,
            "Total": penalty,
            "Settlement_Date": date,
        }
        df = df_sdos.copy()
    else:
        df = df_sdos.loc[df_sdos["Total_CumSum"] <= amount].copy()
        canc = df["Total"].sum()
        saldo = amount - canc
        if saldo > 0:
            id = len(df)
            df.loc[id] = df_sdos.loc[len(df)]
            if df.at[id, "Capital"] > saldo:
                df.at[id, "Capital"] = saldo
                df.at[id, "Interest"] = 0.0
                df.at[id, "IVA"] = 0.0
            else:
                df.at[id, "Interest"] = (saldo - df.at[id, "Capital"]) / 1.21
                df.at[id, "IVA"] = saldo - df.at[id, "Interest"]
                df.at[id, "Total"] = saldo
        elif saldo < 0:
            raise ValueError(f"El saldo es negativo ($ {saldo:,.2f}).")

    df["Type_ID"] = type.ID
    if total_deuda < amount:
        print(CollectionType.PENALTY.ID)
        df.at[penalty_id, "Type_ID"] = CollectionType.PENALTY.ID
    inst_per_cancel = df.loc[(df["Due_Date"] > date), "Installment_ID"].unique()
    df_inst = pd.read_sql("installments", engine, index_col="ID")
    df_inst = df_inst.loc[df_inst.index.isin(inst_per_cancel)]
    df_inst = df_inst.merge(
        df.loc[
            df["Installment_ID"].isin(inst_per_cancel), ["Installment_ID", "Capital"]
        ],
        left_index=True,
        right_on="Installment_ID",
        how="left",
        suffixes=["", "_x"],
    )
    df_inst["Capital"] -= df_inst["Capital_x"]
    df.drop(columns=["ID", "Total_CumSum"], inplace=True)
    df_inst["Type_ID"] = CollectionType.BONIFICACION.ID
    df_inst = df_inst.loc[df_inst["Capital"] == 0, df.columns]

    df_inst["Due_Date"] = df_inst["Due_Date"].dt.to_period("D")

    df = pd.concat([df, df_inst])
    df["Date"] = date
    df = df[
        ["Installment_ID", "Date", "Type_ID", "Capital", "Interest", "IVA", "Total"]
    ]

    df.to_sql("collections", engine, index=False, if_exists="append")

    return df
