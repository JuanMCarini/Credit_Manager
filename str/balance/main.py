from datetime import datetime

import pandas as pd
from pandas import DataFrame, Period

from str.categories import MONEY_COLS
from str.database import read_table


def balance(date: str | datetime | Period = Period.now("D")) -> DataFrame:
    """
    Compute the outstanding balance of all installments up to a given date.

    This function:
        - Loads credits, installments, and collections from the database.
        - Restricts installments and collections to those with disbursement/collection
          dates up to the provided cutoff date.
        - Merges collections onto installments to subtract paid amounts.
        - Returns a DataFrame with updated outstanding capital, interest, IVA, and total.

    Parameters
    ----------
    date : str | datetime | Period, optional
        Cutoff date for the balance calculation. Defaults to today's date as a Period.

    Returns
    -------
    DataFrame
        A DataFrame of installments with updated balances after subtracting collections.
    """

    # --- Load database tables ---
    df_crts = read_table("credits")
    df_inst = read_table("installments")
    df_coll = read_table("collections")

    # Convert input date to Period for comparison
    date = Period(date, "D")

    # --- Merge disbursement date onto installments ---
    df_inst = df_inst.merge(
        df_crts[["Disbursement_Date"]],
        left_on="Credit_ID",
        right_index=True,
        how="left",
    ).copy()

    # Keep only installments from credits disbursed on or before `date`
    df = df_inst.loc[df_inst["Disbursement_Date"] <= date].copy()

    # Keep only collections up to `date`
    df_coll = df_coll.loc[df_coll["Date"] <= date]
    df_coll = df_coll.groupby("Installment_ID")[
        ["Capital", "Interest", "IVA", "Total"]
    ].sum()
    # --- Merge collections onto installments ---
    df = df.merge(
        df_coll[["Capital", "Interest", "IVA", "Total"]],
        left_index=True,
        right_index=True,
        how="left",
        suffixes=("", "_Coll"),
    )
    df.index.name = "ID"
    # --- Subtract collected amounts from installment balances ---
    for col in MONEY_COLS:
        # Convert collections to numeric (safely), fill missing with zero
        df[col + "_Coll"] = pd.to_numeric(df[col + "_Coll"], errors="coerce").fillna(
            0.0
        )

        # Subtract collected amount
        df[col] -= df[col + "_Coll"]
        df[col] = df[col].round(6)

        # Remove helper column
        df.drop(columns=[col + "_Coll"], inplace=True)

    # --- Drop columns not needed in the output ---
    df.drop(
        columns=["Disbursement_Date", "Settlement_Date"],
        inplace=True,
    )

    return df
