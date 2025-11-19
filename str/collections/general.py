# ------------------------------------------------------------
# collections/general.py
# ------------------------------------------------------------
# Shared utilities for the collections subsystem.
#
# This module provides the core building blocks used by
# *all* collection types (common, advance, bonus, penalties).
#
# Responsibilities:
#   • Reading and writing collection rows to the database.
#   • Standard formatting for collection DataFrames.
#   • Rounding and normalizing pending balances.
#   • Definitions of the canonical columns used in collection
#     operations (Installment_ID, Date, Type_ID, etc.).
#
# These functions define the “common rules” that every
# collection module must follow, ensuring consistency across
# penalties, advances, common payments, and bonuses.
# ------------------------------------------------------------

from datetime import datetime

from pandas import DataFrame, Period

# Utility for rounding small balances
from str.collections.round import round_balance

# Database I/O helpers
from str.database import read_table, write_table

# Lookup table with collection types
df_coll_type = read_table("collection_types")

# Standard column names for all collection operations
coll_columns = [
    "Installment_ID",
    "Date",
    "Type_ID",
    "Capital",
    "Interest",
    "IVA",
    "Total",
]


def split(
    df: DataFrame, amount: float, type_id: int
) -> tuple[DataFrame, DataFrame, float]:
    """
    ------------------------------------------------------------
    split()
    ------------------------------------------------------------
    Split a payment across installments, determining:

      • df_up   → installments fully covered by the payment
      • df_down → remaining installments (partially or not covered)
      • surplus → leftover money after fully covering df_up

    The function never modifies installment amounts; it only
    partitions the DataFrame logically based on cumulative totals.

    Parameters
    ----------
    df : DataFrame
        Installments to evaluate.
    amount : float
        Payment amount applied.
    type_id : int
        Type_ID to assign to the fully covered installments.

    Returns
    -------
    tuple(DataFrame, DataFrame, float)
        df_up, df_down, surplus
    ------------------------------------------------------------
    """

    # Ensure installments are processed in chronological order
    df = df.sort_values(by=["Due_Date"])

    # Compute running totals to determine up to where the payment reaches
    df["Cum_Total"] = df["Total"].cumsum()

    # ------------------------------------------------------------
    # Identify installments fully covered by the payment (Cum_Total ≤ amount)
    # ------------------------------------------------------------
    df_up = df.loc[(df["Cum_Total"] <= amount)].reset_index(drop=False)
    df_up["Type_ID"] = type_id

    # ------------------------------------------------------------
    # Installments that exceed the payment boundary (partially or not covered)
    # ------------------------------------------------------------
    df_down = df.loc[(df["Cum_Total"] > amount)].reset_index(drop=False)

    # Surplus = money left after paying all installments in df_up
    surplus = amount - df_up["Total"].sum()

    # Clean temporary working column
    df_up.drop(columns=["Cum_Total"], inplace=True)
    df_down.drop(columns=["Cum_Total"], inplace=True)

    return df_up, df_down, surplus


def first_inst(df_down: DataFrame, surplus: float, type_id: int) -> DataFrame:
    """
    ------------------------------------------------------------
    first_inst()
    ------------------------------------------------------------
    Apply the surplus amount to the *next* pending installment.

    This function takes the first installment in `df_down`—
    meaning the first installment that was not fully covered
    by previous payments—and allocates the remaining `surplus`
    as a partial payment.

    Logic preserved exactly as in the original model:

        • If surplus < Capital:
              Capital = surplus
              Interest = 0
              IVA = 0

        • If surplus ≥ Capital:
              Capital = fully paid
              Remaining amount is allocated to:
                    Interest  = (surplus - capital) / 1.21
                    IVA       = surplus - (capital + interest)

        • The resulting Total is always equal to the entire surplus.

    Parameters
    ----------
    df_down : DataFrame
        DataFrame containing the installments that remain unpaid
        after fully covering earlier ones. Only the *next* one
        will be partially paid.
    surplus : float
        Remaining amount of the payment after fully paying
        previous installments.
    type_id : int
        Type_ID to tag the resulting partial installment
        (e.g., "COMUN", "ANTICIPO", etc.).

    Returns
    -------
    DataFrame
        A single-row DataFrame representing the partially paid
        next installment. Empty if no installment exists.
    ------------------------------------------------------------
    """

    # If no installments remain, nothing to apply
    if df_down.empty or surplus == 0.0:
        return df_down.iloc[0:0].copy()

    # Select exactly the next pending installment (smallest index)
    df = df_down.loc[[df_down.index.min()]]

    # Extract capital as numeric (avoids dtype issues)
    capital = float(df.at[0, "Capital"])  # type: ignore

    # ------------------------------------------------------------
    # Case 1: Surplus only covers part of the capital
    # ------------------------------------------------------------
    if capital > surplus:
        df.at[0, "Capital"] = surplus
        df.at[0, "Interest"] = 0.0
        df.at[0, "IVA"] = 0.0

    # ------------------------------------------------------------
    # Case 2: Surplus covers all capital and leaves a remainder
    #         for Interest + IVA using the 21% VAT split
    # ------------------------------------------------------------
    else:
        # Interest computed net of IVA (since Total = I + IVA)
        interest = (surplus - capital) / 1.21
        df.at[0, "Interest"] = interest

        # IVA is the leftover after capital + interest
        df.at[0, "IVA"] = surplus - (capital + interest)

    # Update the total equal to the surplus applied
    df.at[0, "Total"] = surplus

    # Mark the installment with the provided Type_ID
    df["Type_ID"] = type_id

    # Remove rows where Total == 0 (should not happen but kept by your logic)
    df = df.loc[df["Total"] != 0.0]

    return df


def _save(
    df: DataFrame, date: str | datetime | Period = Period.now("D"), save: bool = True
) -> DataFrame:
    """
    ------------------------------------------------------------
    _save()
    ------------------------------------------------------------
    Persist collection rows to the database (if save=True) and
    return only the newly inserted rows.

    Workflow:
      • If save is False:
            → simply return the input DataFrame (no DB changes).
      • If save is True:
            → read existing rows from "collections"
            → write the new rows
            → read the table again
            → keep only the rows that were just inserted
            → call round_balance(date) to clean tiny residuals.

    Parameters
    ----------
    df : DataFrame
        Collection rows to be saved.
    date : str | datetime | Period
        Date used by round_balance to normalize balances.
    save : bool
        Flag indicating whether to write to the database or not.

    Returns
    -------
    DataFrame
        If save=True: only the newly inserted collection rows.
        If save=False: the original df (unchanged).
    ------------------------------------------------------------
    """

    if save:
        table = "collections"

        # Snapshot of existing collection IDs before inserting
        df_coll = read_table(table)
        old_coll = df_coll.index.values

        # Write the new collections into the table
        write_table(df, table)

        # Reload table and keep only the newly inserted rows
        df_coll = read_table(table)
        df = df_coll.loc[~df_coll.index.isin(old_coll)].copy()

        # Normalize any tiny residual balances on the given date
        round_balance(date)

    return df


def basic_formatting(
    df: DataFrame, date: str | datetime | Period = Period.now("D")
) -> DataFrame:
    """
    ------------------------------------------------------------
    basic_formatting()
    ------------------------------------------------------------
    Standardize the structure of a collections DataFrame so that
    it matches the canonical schema required by the system.

    Formatting steps (logic unchanged):
      • Remove leftover working columns like "Cum_Total".
      • Rename "ID" → "Installment_ID" when needed.
      • If the DataFrame has no "Installment_ID" column, convert
        the index into that column.
      • Assign the collection date.
      • Keep only the canonical columns defined in coll_columns.

    Parameters
    ----------
    df : DataFrame
        Collection rows to format.
    date : str | datetime | Period
        Payment date to store in the output rows.

    Returns
    -------
    DataFrame
        A clean, standardized DataFrame ready for saving.
    ------------------------------------------------------------
    """

    # Remove cumulative total column if present (from split logic)
    df.drop(columns=["Cum_Total"], inplace=True, errors="ignore")

    # Standard column name expected across all collections
    df.rename(columns={"ID": "Installment_ID"}, inplace=True)

    # If missing, generate Installment_ID from the index
    if "Installment_ID" not in df.columns:
        df.index.name = "Installment_ID"
        df.reset_index(drop=False, inplace=True)

    # Assign the payment date to all rows
    df["Date"] = date

    # Keep only the canonical collection columns
    df = df[coll_columns]

    return df


def extra_formatting(df: DataFrame) -> DataFrame:
    """
    ------------------------------------------------------------
    extra_formatting()
    ------------------------------------------------------------
    Final human-friendly formatting applied after saving or
    generating collection rows.

    Operations performed (logic unchanged):
      • Convert the numeric Type_ID into the readable "Type"
        using df_coll_type.
      • Remove the Type_ID column.
      • Reorder columns for presentation-friendly output.

    Parameters
    ----------
    df : DataFrame
        The collection rows already processed and formatted.

    Returns
    -------
    DataFrame
        A human-readable version of the collection records.
    ------------------------------------------------------------
    """

    # Replace numerical Type_ID with its human-readable description
    df["Type"] = df["Type_ID"].map(df_coll_type["Type"])

    # Remove the raw Type_ID column
    df.drop(columns=["Type_ID"], inplace=True)

    # Reorder columns to the preferred final layout
    df = df[["Installment_ID", "Date", "Type", "Capital", "Interest", "IVA", "Total"]]

    return df
