# collections/penalty.py

from datetime import datetime

from pandas import DataFrame, Period

from str.collections.type_coll import penalty_id
from str.database import read_table
from str.database.structure import Credit


def new(
    credit: int, amount: float, date: str | datetime | Period = Period.now("D")
) -> DataFrame:
    # create a penalty credit for the surplus ---
    df_crts = read_table("credits")
    df_clts = read_table("clients")

    # Get client and organism from original credit
    id_client = int(df_crts.at[credit, "Client_ID"])  # type: ignore
    client_cuil = int(df_clts.at[id_client, "CUIL"])  # type: ignore
    organism_id = int(df_crts.at[credit, "Organism_ID"])  # type: ignore
    # Create a new penalty credit for the surplus
    new_penalty = Credit(
        date,
        0.0,
        amount,
        "PENALTY",
        client_cuil,
        organism_id,
        Emission_Date=date,
    )
    # Get its installments and prepare them for insertion
    new_penalty = new_penalty.Installments.reset_index(drop=False)
    df_inst = read_table("installments")
    # Assign ID based on current max index in installments table
    new_penalty["ID"] = df_inst.index.max()
    new_penalty = new_penalty[
        [
            "ID",
            "Credit_ID",
            "Inst_Num",
            "Owner_ID",
            "Due_Date",
            "Capital",
            "Interest",
            "IVA",
            "Total",
        ]
    ]
    new_penalty["Type_ID"] = penalty_id

    return new_penalty
