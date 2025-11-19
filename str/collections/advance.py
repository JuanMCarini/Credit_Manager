# ------------------------------------------------------------
# collections/advance.py
# ------------------------------------------------------------
# Tools for handling advance-type collections (adelantos) applied
# to credit installments. This module:
#   • Retrieves active installment balances.
#   • Splits a payment into covered installments, pending ones,
#     and surplus.
#   • Creates new penalty or bonus installments when needed.
#   • Applies formatting and persistence rules used across the
#     collections subsystem.
#
# All functions here operate at the “advance collection” level,
# meaning they implement the logic used when a partial or full
# prepayment is applied to a credit.
# ------------------------------------------------------------

from datetime import datetime

from pandas import DataFrame, Period, concat

# Load balances of installments
from str.balance import balance

# Shared tools for collections: saving, formatting, splitting, etc.
from str.collections.general import (
    _save,
    basic_formatting,
    extra_formatting,
    first_inst,
    split,
)

# Penalty generator (used when surplus creates a new installment)
from str.collections.penalty import new as penalty

# IDs representing advance/bonus collection types
from str.collections.type_coll import advance_id, bonus_id

# Load collection types table (indexed by "Type")
from str.database import read_table

df_coll_type = read_table("collection_types", "Type")


def build_bonus_rows(
    df_original: DataFrame,
    df_result: DataFrame,
    advance_id: int,
    bonus_id: int,
    date: str | datetime | Period,
) -> DataFrame:
    """
    ------------------------------------------------------------
    build_bonus_rows()
    ------------------------------------------------------------
    Build "bonus" installments when:
      - An installment has been collected as an advance (Type_ID = advance_id),
      - Capital is fully paid, but there is still interest/IVA structure
        that must be recognized as a separate bonus row.

    Parameters
    ----------
    df_original : DataFrame
        Original installments (before applying the advance collection).
    df_result : DataFrame
        Resulting installments after applying the advance collection.
    advance_id : int
        Type_ID used for advance installments.
    bonus_id : int
        Type_ID that will be assigned to the generated bonus rows.
    date : str | datetime | Period
        Date used for basic_formatting.

    Returns
    -------
    DataFrame
        Formatted bonus rows ready to be concatenated to df_result.
    ------------------------------------------------------------
    """

    # Merge original installments with the collected Capital/Interest
    df_int = df_original.merge(
        df_result.loc[
            df_result["Type_ID"] == advance_id,
            ["Installment_ID", "Capital", "Interest"],
        ],
        left_index=True,
        right_on="Installment_ID",
        suffixes=["", "_Coll"],
    )

    # Compute remaining capital/interest after collection
    df_int["Capital"] -= df_int["Capital_Coll"]
    df_int["Interest"] -= df_int["Interest_Coll"]

    # Keep only those with zero capital but positive interest (bonus case)
    df_int = df_int.loc[(df_int["Capital"] == 0.0) & (df_int["Interest"] != 0.0)]

    # Recompute total and assign bonus type
    df_int["Total"] = df_int[["Capital", "Interest", "IVA"]].sum(axis=1)
    df_int.drop(columns=["Capital_Coll", "Interest_Coll"], inplace=True)
    df_int["Type_ID"] = bonus_id

    # Apply the same formatting as the rest of the flows
    df_int = basic_formatting(df_int, date)

    return df_int


def credit(
    credit_id: int,
    amount: float,
    date: str | datetime | Period = Period.now("D"),
    save: bool = False,
) -> DataFrame:
    """
    ------------------------------------------------------------
    credit()
    ------------------------------------------------------------
    Compute the effect of applying a payment (amount) to a credit.

    This function:
      • Loads the credit balance at the given date.
      • Removes future interest/IVA from installments not yet due.
      • Splits the payment into 'covered' installments (df_up),
        partially covered or uncovered ones (df_down),
        and calculates any surplus.
      • Creates penalties or next installments when necessary.
      • Builds EXTRA bonus rows when interest disappears
        but IVA remains.
      • Formats, saves (optional), and returns the final DataFrame.

    Parameters
    ----------
    credit_id : int
        Identifier of the credit to operate on.
    amount : float
        Amount of money being applied.
    date : str | datetime | Period
        Date of the transaction.
    save : bool
        Whether to save the result to the database.

    Returns
    -------
    DataFrame
        The final combined result of all applied installments.
    ------------------------------------------------------------
    """

    # Load the balance and filter only installments of this credit
    df = balance(date)
    df = df.loc[df["Credit_ID"] == credit_id]

    # Copy original DF for later internal-interest comparison
    df_int = df.copy()

    # Remove interest and IVA from future installments
    for col in ["Interest", "IVA"]:
        df.loc[df["Due_Date"] >= date, col] = 0.0

    # Recompute each installment's total after adjustment
    df["Total"] = df[["Capital", "Interest", "IVA"]].sum(axis=1)

    # Split payment into fully covered installments (up),
    # remaining installments (down), and any surplus
    df_up, df_down, surplus = split(df, amount, advance_id)

    # Handle surplus cases
    if surplus > 0:
        if df_down.empty and save:
            # Create a penalty installment if allowed
            new_penalty = penalty(credit_id, surplus, date)
            df = concat([df_up, new_penalty])
            df.set_index("ID", inplace=True)

        elif df_down.empty:
            # Surplus exists but saving is not allowed -> warn
            df = df_up.copy()
            print(f'❗❗❗ We need to create a "Penalty" for $ {surplus:,.2f}. ❗❗❗')

        else:
            # Partially covered: create/update the next installment
            next_inst = first_inst(df_down, surplus, advance_id)
            df = concat([df_up, next_inst])
            df.set_index("ID", inplace=True)

            # Recompute true surplus after applying the next installment
            surplus = amount - df["Total"].sum()

    else:
        # No surplus, everything fits neatly in df_up
        df = df_up.copy()

    # Format the resulting covered/updated installments
    df = basic_formatting(df, date)

    # Generate the bonus installments (if any) and append them to the main DataFrame
    df_bonus = build_bonus_rows(df_int, df, advance_id, bonus_id, date)

    # Merge the newly created bonus rows with the existing result
    if not df_bonus.empty:
        df = concat([df, df_bonus])

    # Save to DB if requested
    _save(df, date, save)

    # Apply any extra formatting before returning
    df = extra_formatting(df)

    return df
