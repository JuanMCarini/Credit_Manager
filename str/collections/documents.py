# ------------------------------------------------------------
# collections/documents.py
# ------------------------------------------------------------
# Main processing layer for handling collection operations.
#
# This module orchestrates:
#   • Document-level collections
#   • Credit-level collections (common / advance)
#   • Installment selection and surplus allocation logic
#
# It acts as the “dispatcher” that decides which collection
# strategy to apply based on the chosen CollectionType.
# ------------------------------------------------------------

from datetime import datetime

from pandas import DataFrame, Period, concat

# Enum definitions for collection types and document types
from str.categories import CollectionTypes, DocTypes
from str.collections.advance import credit as advance_coll

# Credit-level collection handlers
from str.collections.common import credit as common_coll

# Core collection utilities:
#   - split: break payment into fully-covered / pending installments
#   - first_inst: apply surplus to the next pending installment
#   - get_client_balance_by_document: retrieve all installments for a document
from str.collections.tools import (
    first_inst,
    get_client_balance_by_document,
    split,
)

# Identifiers for collection types
from str.collections.type_coll import advance_id, common_id


def document(
    doc: int | str,
    doc_type: DocTypes,
    collection_type: CollectionTypes,
    amount: float,
    date: str | datetime | Period = Period.now("D"),
    save: bool = False,
) -> DataFrame:
    """
    ------------------------------------------------------------
    document()
    ------------------------------------------------------------
    Apply a payment at *document level* (DNI / CUIL) and distribute
    it across all credits of that client, using either:
      • common collection logic ("COMUN"), or
      • advance collection logic ("ANTICIPADA").

    Workflow:
      1) Load all installments for all credits linked to (doc, doc_type)
         at the given date.
      2) Choose the collection function and Type_ID according to
         `collection_type`.
         - For ANTICIPADA: remove future Interest / IVA and recompute Total.
      3) At document level, split the payment into:
           - df_up   → fully covered installments
           - df_down → remaining installments
           - surplus → leftover amount
      4) Use `first_inst()` to apply the surplus to the next installment.
      5) Aggregate the applied amounts per Credit_ID.
      6) For each credit, call the corresponding collection function
         (common_coll / advance_coll).
      7) If there is any remaining surplus, assign it to the last credit.
      8) Filter out rows with Total == 0 and return the result.

    Parameters
    ----------
    doc : int | str
        Document identifier (raw DNI/CUIL/etc.).
    doc_type : DocTypes
        Document type used in the "clients" table.
    collection_type : CollectionTypes
        Type of collection ("COMUN" or "ANTICIPADA").
    amount : float
        Total payment amount at document level.
    date : str | datetime | Period
        Payment date (snapshot for balances).
    save : bool
        Whether to persist the resulting collections.

    Returns
    -------
    DataFrame
        Concatenation of all collection rows generated for this document.
    ------------------------------------------------------------
    """

    # Load all installments belonging to all credits of this client as of the given date
    df = get_client_balance_by_document(doc, doc_type, date)

    # ------------------------------------------------------------
    # Choose collection behavior based on collection_type
    # ------------------------------------------------------------
    if collection_type == "COMUN":
        collection = common_coll
        type_id = common_id

    elif collection_type == "ANTICIPADA":
        collection = advance_coll
        type_id = advance_id

        # Remove interest and IVA from future installments
        for col in ["Interest", "IVA"]:
            df.loc[df["Due_Date"] > date, col] = 0.0

        # Recompute each installment's total after adjustment
        df["Total"] = df[["Capital", "Interest", "IVA"]].sum(axis=1)

    else:
        # Unsupported or unknown collection type
        raise ValueError(f"⚠️⚠️⚠️ {collection_type} is not a valid collection type. ⚠️⚠️⚠️")

    # --- Split payment at document level ---
    df_up, df_down, surplus = split(df, amount, type_id)

    # Use surplus to partially pay the next installment, if any
    next_inst = first_inst(df_down, surplus, type_id)

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
        dfs.append(collection(id, credit_amount, date, save))

    # If there is remaining surplus, allocate it to the last credit
    if surplus > 0:
        dfs.append(collection(df.index.max(), surplus, date, save))

    # Concatenate all collection DataFrames into a single output
    df = concat([df for df in dfs])

    # Remove rows with zero total (defensive clean-up)
    df = df.loc[df["Total"] != 0]

    return df
