# ------------------------------------------------------------
# collections/process/massive.py
# ------------------------------------------------------------
# Massive collection processing utilities.
#
# This module provides tools to:
#   • Load a massive collection file (Excel/CSV)
#   • Aggregate collection amounts by identification type
#   • Dispatch each aggregated entry to the individual
#     collection engine
#   • Return a detailed DataFrame of processed installments
# ------------------------------------------------------------

from datetime import datetime

from pandas import DataFrame, Period, concat, read_csv, read_excel

from str.categories import CollectionTypes, IdentificationType
from str.collections.general import individual_collection
from str.database import read_table
from str.io import select_file


def collection(
    collection_type: CollectionTypes,
    ident_type: IdentificationType,
    date: str | datetime | Period = Period.now("D"),
    save: bool = False,
) -> DataFrame:
    """
    ------------------------------------------------------------
    process_massive_collection()
    ------------------------------------------------------------
    Process a massive collection file and apply collections
    entry-by-entry using the individual_collection() engine.

    Workflow (logic preserved):
      1. Ask the user to select a file (.xlsx or .csv).
      2. Read the file into a DataFrame.
      3. Validate that the identification column (ident_type)
         exists in the file.
      4. Group by ident_type and sum the "Monto" column.
      5. For each identifier:
             → call individual_collection() with the aggregated
               amount.
      6. Concatenate all individual results into a single
         DataFrame.
      7. Enrich the result with installment data from the
         "installments" table (Credit_ID, Inst_Num, Due_Date).
      8. Return a cleaned DataFrame with the most relevant
         columns.

    Parameters
    ----------
    collection_type : CollectionTypes
        Collection mode ("COMUN", "ANTICIPADA", etc.).
    ident_type : IdentificationType
        Column name used as identifier in the input file
        (e.g. "DNI", "CUIL", "Credit_ID").
    date : str | datetime | Period, optional
        Reference date for the collection process.
    save : bool, optional
        Whether to persist the generated movements.

    Returns
    -------
    DataFrame
        Detailed collection movements, one row per processed
        installment.

    Raises
    ------
    ValueError
        If:
          • No file is selected
          • The file extension is not supported
          • ident_type is not found in the file
          • "Monto" column is missing
    ------------------------------------------------------------
    """

    # --- 1) Select input file interactively ---
    path = select_file()
    if not path:
        raise ValueError("No file selected for massive collection processing.")

    # --- 2) Load file depending on extension ---
    if path.endswith(".xlsx"):
        df = read_excel(path)
    elif path.endswith(".csv"):
        df = read_csv(path)
    else:
        raise ValueError(f"Unsupported file type: {path}. Use .xlsx or .csv.")

    # --- 3) Validate required columns ---
    if ident_type not in df.columns:
        raise ValueError(
            f"{ident_type} is not in the file. Columns: {df.columns.values}"
        )

    if "Monto" not in df.columns:
        raise ValueError(
            f"'Monto' column is not in the file. Columns: {df.columns.values}"
        )

    # --- 4) Aggregate amount by identifier ---
    df = df.groupby(ident_type)[["Monto"]].sum()
    print(f"Total collection amount: $ {df['Monto'].sum():,.2f}")

    # --- 5) Run individual collection for each identifier ---
    dfs: list[DataFrame] = []
    for doc in df.index:
        amount: float = df.at[doc, "Monto"]  # type: ignore
        dfs.append(
            individual_collection(doc, ident_type, collection_type, amount, date, save)
        )

    # --- 6) Concatenate all individual results ---
    df = concat(dfs)

    # --- 7) Enrich with installments information ---
    df_inst = read_table("installments")
    df = df.merge(
        df_inst[["Credit_ID", "Inst_Num", "Due_Date"]],
        left_on="Installment_ID",
        right_index=True,
    )

    # --- 8) Keep only the most relevant columns for reporting ---
    df = df[
        [
            "Type",
            "Date",
            "Credit_ID",
            "Inst_Num",
            "Due_Date",
            "Capital",
            "Interest",
            "IVA",
            "Total",
        ]
    ]

    return df
