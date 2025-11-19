# ------------------------------------------------------------
# collections/common.py
# ------------------------------------------------------------
# Logic for handling *common* (regular) collections applied to
# credit installments. These differ from advance-type collections
# because:
#   • They do not remove future interest/IVA.
#   • They follow the natural chronological flow of installments.
#   • Surplus handling may create penalties only when allowed.
#
# This module centralizes the workflow for everyday payments:
#   - Retrieve current balances
#   - Split the incoming amount into covered and pending portions
#   - Apply surplus to the next installment or generate penalties
#   - Apply the shared formatting and saving conventions used by
#     all collection modules
#
# The functions provided here are used by the main collection
# pipeline whenever a standard payment (Type = common_id) occurs.
# ------------------------------------------------------------

from datetime import datetime

from pandas import DataFrame, Period, concat

# Retrieve the current balance of installments for a given date
from str.balance import balance

# Allowed document types (e.g. "DNI", "CUIL")
from str.categories import DocTypes

# Shared tools for formatting, saving, and installment operations
from str.collections.general import (
    _save,
    basic_formatting,
    extra_formatting,
    first_inst,
    split,
)

# Function to generate penalty installments when necessary
from str.collections.penalty import new as penalty

# Identifier for common/regular collection type
from str.collections.type_coll import common_id

# Read tables from the database (clients, credits, etc.)
from str.database import read_table

# CUIL validator (normalizes and checks checksum)
from str.database.structure.clients.tool import validate_cuil


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
    Apply a payment (amount) to a given credit and return the
    updated set of installments affected by the operation.

    The function:
      • Loads the active installments for the given credit/date.
      • Splits the payment into fully covered installments (df_up),
        pending/remaining installments (df_down), and surplus money.
      • Handles surplus by updating the next installment or creating
        a penalty installment if allowed.
      • Applies standard formatting, optional saving, and final
        beautification before returning the resulting DataFrame.

    Parameters
    ----------
    credit_id : int
        ID of the credit being paid.
    amount : float
        Money being applied to the credit.
    date : str | datetime | Period
        Date of the payment.
    save : bool
        Whether new installments (like penalties) should be saved.

    Returns
    -------
    DataFrame
        The formatted and updated installments after applying payment.
    ------------------------------------------------------------
    """

    # --- Get current balance of installments for the given date ---
    df = balance(date)

    # Keep only installments from this credit and with positive pending balance
    df = df.loc[(df["Credit_ID"] == credit_id) & (df["Total"] > 0.0)]

    # Split payment: fully covered installments, remaining installments, and surplus
    df_up, df_down, surplus = split(df, amount, common_id)

    if surplus > 0:
        # Extra money remains after covering df_up
        if not df_down.empty:
            # Apply surplus to the next pending installment
            next_inst = first_inst(df_down, surplus, common_id)

            # Merge fully covered installments with the partially covered one
            df = concat([df_up, next_inst])
            df.set_index("ID", inplace=True)

        elif save:
            # Surplus exists but no pending installments: create a penalty
            new_penalty = penalty(credit_id, amount)

            # Merge fully covered installments with the new penalty installment
            df = concat([df_up.reset_index(drop=False), new_penalty])
            df.set_index("ID", inplace=True)

        else:
            # Surplus exists but creation of penalty is not allowed
            print(f'❗❗❗ We need to create a "Penalty" for $ {surplus:,.2f}. ❗❗❗')

    else:
        # Payment exactly fits the fully covered installments
        df = df_up.copy()
        df.set_index("ID", inplace=True)

    # Apply standard formatting to installments
    df = basic_formatting(df, date)

    # Save installments if required by the caller
    df = _save(df, date, save)

    # Apply final formatting (sorting, renaming, cosmetic adjustments)
    df = extra_formatting(df)

    return df


def document(
    doc: int | str,
    doc_type: DocTypes,
    amount: float,
    date: str | datetime | Period = Period.now("D"),
    save: bool = False,
) -> DataFrame:
    """
    ------------------------------------------------------------
    document()
    ------------------------------------------------------------
    Apply a payment at *document level* (DNI/CUIL) and distribute
    it across all credits of that client in due-date order.

    Workflow (logic preserved):
      1) Normalize and validate the document according to doc_type.
      2) Look up the client ID from the "clients" table.
      3) Get all credits of that client with disbursement date
         <= `date`.
      4) Get the balance of all installments for those credits.
      5) Sort installments globally by:
            - Due_Date
            - Emission_Date (disbursement date)
            - Credit_ID
      6) Use `split()` to determine:
            - df_up   → fully covered installments
            - df_down → remaining installments
            - surplus → leftover amount at document level
      7) Use `first_inst()` to partially pay the next installment.
      8) Aggregate by Credit_ID to know how much goes to each credit.
      9) For each credit, call `credit()` with its allocated amount.
     10) If there is leftover surplus, apply it to the last credit.

    Parameters
    ----------
    doc : int | str
        Raw document value (DNI/CUIL/etc.).
    doc_type : DocTypes
        Column name used in "clients" as index ("DNI", "CUIL", ...).
    amount : float
        Total payment amount to distribute among the client's credits.
    date : str | datetime | Period
        Payment date.
    save : bool
        Whether to persist the generated collections.

    Returns
    -------
    DataFrame
        Concatenation of all collection DataFrames returned by `credit()`.
    ------------------------------------------------------------
    """

    # --- Normalize and validate the document depending on its type ---
    if doc_type == "CUIL":
        doc = validate_cuil(doc)

    elif doc_type == "DNI":
        # Keep only digits and ensure it fits DNI length constraints
        dni = "".join(ch for ch in str(doc) if ch.isdigit())
        if len(dni) > 8:
            raise ValueError(f"⚠️⚠️⚠️ {dni} no es un DNI. ⚠️⚠️⚠️")
        else:
            doc = int(dni)

    # --- Look up the client ID by document in the clients table ---
    df_clts = read_table("clients", doc_type)
    client_id = df_clts.at[doc, "ID"]

    # --- Get all credits for that client up to the given date ---
    df_crts = read_table("credits")
    credits_id = df_crts.loc[
        (df_crts["Client_ID"] == client_id) & (df_crts["Disbursement_Date"] <= date)
    ].index.values

    # --- Load full balance and filter by the client's credits ---
    df = balance(date)
    df = df.loc[df["Credit_ID"].isin(credits_id)]

    # Emission date = disbursement date of each credit (for sorting)
    df["Emission_Date"] = df["Credit_ID"].map(df_crts["Disbursement_Date"])

    # Global ordering: by due date, then emission date, then credit ID
    df = df.sort_values(by=["Due_Date", "Emission_Date", "Credit_ID"])

    # Running total across all installments (document-level)
    df["Cum_Total"] = df["Total"].cumsum()

    # --- Split payment at document level ---
    df_up, df_down, surplus = split(df, amount, common_id)

    # Use surplus to partially pay the next installment, if any
    next_inst = first_inst(df_down, surplus, common_id)

    # Combine fully-covered installments with the partially paid one
    if not (df_up.empty or next_inst.empty):
        df = concat([df_up, next_inst])
    elif df_up.empty:
        df = next_inst.copy()
    else:
        df = df_up.copy()

    # --- Aggregate payment per credit ---
    df = df.groupby("Credit_ID")[["Total"]].sum()

    # Recompute surplus after summing per credit
    surplus = amount - df["Total"].sum()

    # --- For each credit, call credit() with its allocated amount ---
    dfs: list[DataFrame] = []
    for id in df.index:
        credit_amount: float = df.at[id, "Total"]  # type: ignore
        dfs.append(credit(id, credit_amount, date, save))

    # If there is remaining surplus, allocate it to the last credit
    if surplus > 0:
        dfs.append(credit(max(credits_id), surplus, date, save))

    # Concatenate all collection DataFrames into a single output
    df = concat([df for df in dfs])

    return df
