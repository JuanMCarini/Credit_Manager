# collections/round.py

from datetime import datetime

from pandas import DataFrame, Period

from str.balance import balance
from str.collections.type_coll import round_id
from str.database import write_table


def round_balance(
    date: str | datetime | Period = Period.now("D"), save: bool = True
) -> DataFrame:
    """
    Create rounding adjustments ("REDONDEO") for installments with tiny remaining balances.

    This function:
        - Retrieves the current balance of all installments.
        - Filters installments whose remaining Total is below 0.01 (i.e., rounding dust).
        - Builds a collection entry to zero out those tiny balances.
        - Optionally saves those entries into the `collections` table.

    Parameters
    ----------
    date : str | datetime | Period, optional
        Date assigned to the rounding collection. Defaults to today's date.
    save : bool, optional
        Whether to write the rounding entries into the collections table.
        Defaults to True.

    Returns
    -------
    DataFrame
        A DataFrame containing the rounding collection entries created.
        Columns: ['Installment_ID', 'Date', 'Type_ID', 'Capital', 'Interest', 'IVA', 'Total'].
    """

    # --- Compute full balance up to today (or the given date) ---
    df = balance(date)

    # Keep only installments whose balance is effectively zero
    df = df.loc[(df["Total"].abs() != 0) & (df["Total"] < 0.1)]
    # Prepare index and metadata
    df.index.name = "Installment_ID"
    df.reset_index(drop=False, inplace=True)
    df["Date"] = date

    # Assign the REDONDEO type
    df["Type_ID"] = round_id

    # Keep only required columns for writing to the collections table
    df = df[
        ["Installment_ID", "Date", "Type_ID", "Capital", "Interest", "IVA", "Total"]
    ]
    # Save to database if required
    if save:
        write_table(df, "collections")

    return df
