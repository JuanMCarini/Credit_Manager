# collections/general.py

from datetime import datetime

from pandas import DataFrame, Period

# Retrieve the full installment balance snapshot for a given date
# Allowed document types (e.g. "DNI", "CUIL")
from str.categories import CollectionTypes, IdentificationType
from str.collections.advance import credit as advance
from str.collections.common import credit as common
from str.collections.documents import document

# Utility for rounding small balances
# Database I/O helpers
from str.database import read_table

# CUIL validator (normalizes and checks checksum)

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


def individual_collection(
    ident: int | str,
    ident_type: IdentificationType,
    collection_type: CollectionTypes,
    amount: float,
    date: str | datetime | Period = Period.now("D"),
    save: bool = False,
) -> DataFrame:
    """
    ------------------------------------------------------------
    general()
    ------------------------------------------------------------
    Dispatch function that routes the request to the appropriate
    collection handler depending on the identification type and
    collection type.

    Behavior preserved exactly as in your original logic:
      • ident_type in {"DNI", "CUIL"}:
            → handled by document()
      • ident_type == "Credit_ID":
            → handled by common() or advance()
              depending on collection_type
      • ident_type == "Origin_ID":
            → returns an empty DataFrame (placeholder behavior)
      • otherwise:
            → raises ValueError

    Parameters
    ----------
    ident : int | str
        Identification value (DNI, CUIL, credit ID, etc.).
    ident_type : IdentificationType
        Type of identification ("DNI", "CUIL", "Credit_ID", ...).
    collection_type : CollectionTypes
        Collection mode ("COMUN" or "ANTICIPADA").
    amount : float
        Amount to collect.
    date : str | datetime | Period
        Reference date for the operation.
    save : bool, optional
        Whether to persist the result to the database.

    Returns
    -------
    DataFrame
        The result of the dispatched collection handler.

    Raises
    ------
    ValueError
        If an unsupported identification type is provided.
    ------------------------------------------------------------
    """

    # --- Dispatch by identification type ---
    if ident_type in ["DNI", "CUIL"]:
        df = document(ident, ident_type, collection_type, amount, date, save)  # type: ignore

    elif ident_type == "Credit_ID":
        # Select the correct collection handler
        if collection_type == "COMUN":
            df = common(ident, amount, date, save)  # type: ignore
        elif collection_type == "ANTICIPADA":
            df = advance(ident, amount, date, save)  # type: ignore
        else:
            raise ValueError(f"Unsupported collection type: {collection_type}")

    elif ident_type == "Origin_ID":
        # Placeholder behavior remains unchanged
        df = DataFrame()

    else:
        raise ValueError(f"⚠️⚠️⚠️ {ident_type} is not a valid identification type. ⚠️⚠️⚠️")

    return df
