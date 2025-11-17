from datetime import datetime

from pandas import DataFrame, Period

from str.categories import CreditTypes
from str.database.connection import read_table, write_table
from str.database.structure import (
    Client,
    search_client_id,
)
from str.database.structure.installments import Installment
from str.database.structure.organisms import Organism, search_organism_id
from str.tool import _log, log


class Credit:
    def _to_dataframe(self) -> DataFrame:
        return DataFrame(
            [
                {
                    "Origin_ID": self.Origin_ID,
                    "Disbursement_Date": self.Emission_Date,
                    "First_Due_Date": self.Due_Date,
                    "Capital_Requested": self.Capital_Requested,
                    "Capital": self.Capital,
                    "Credit_Type_ID": self.Credit_Type,
                    "TNA_C_IVA": self.TNA_C_IVA,
                    "Term": self.Term,
                    "Client_ID": self.Client_ID,
                    "Organism_ID": self.Organism_ID,
                    "Purchase_ID": None,
                    "Sale_ID": None,
                }
            ]
        )

    def __init__(
        self,
        Due_Date: str | datetime | Period,
        Capital_Requested: float,
        Capital: float,
        Credit_Type: CreditTypes,
        Client: Client | int | str,
        Organism: Organism | int | str,
        Term: int = 1,
        TNA_C_IVA: float = 0.0,
        Emission_Date: str | datetime | Period = Period.now("D"),
        Origin_ID: int | None = None,
    ):
        table = "credits"

        self.Origin_ID = Origin_ID
        self.Emission_Date = Period(Emission_Date, freq="D")
        self.Due_Date = Period(Due_Date, freq="D")
        self.Capital_Requested = Capital_Requested
        self.Capital = Capital
        df_credit_types = read_table("credit_types", "Name")
        self.Credit_Type = df_credit_types.at[Credit_Type, "ID"]
        self.TNA_C_IVA = TNA_C_IVA
        self.Term = Term
        self.Client_ID = search_client_id(Client)
        self.Organism_ID = search_organism_id(Organism)

        df = read_table(table)
        if (Origin_ID is None) or (Origin_ID not in df.index.values):
            df = self._to_dataframe()
            write_table(df, table)
            df = read_table(table)
            self.ID = int(df.index.values.max())
            _log(f"✅ Credit created with ID {self.ID:08d}.", log)
        else:
            mask = (df["Origin_ID"] == Origin_ID) & (
                df["Client_ID"] == self.Organism_ID
            )
            df = df.loc[mask]
            if df.empty:
                raise ValueError(
                    f"❌ Credit with Origin_ID {self.Origin_ID} and Organism_ID {self.Organism_ID:03d} not found."
                )
            elif len(df) > 1:
                raise ValueError(
                    f"❌ Multiple credits with Origin_ID {self.Origin_ID} and Organism_ID {self.Organism_ID} found."
                )
            else:
                self.ID = int(df.index.values[0])
                _log(
                    f"✅ Credit with Origin_ID {self.Origin_ID} and Organism_ID {self.Organism_ID} found with ID {self.ID:08d}.",
                    log,
                )

        df_inst = DataFrame(
            [Installment(self.ID, i)._to_dict() for i in range(1, self.Term + 1)]
        )
        df_inst.set_index("Inst_Num", inplace=True)
        self.Installments = df_inst

    def __str__(self) -> str:
        return (
            f"ℹ️ Credit ID {self.ID:08d}\n"
            f"    ➡️ Emission_Date: {self.Emission_Date}\n"
            f"    ➡️ Capital_Requested: $ {self.Capital_Requested:,.2f}\n"
            f"    ➡️ Capital: $ {self.Capital:,.2f}\n"
            f"    ➡️ Credit_Type: {self.Credit_Type}\n"
            f"    ➡️ Client_ID: {self.Client_ID}\n"
            f"    ➡️ Organism_ID: {self.Organism_ID}\n"
            f"    ➡️ Term: {self.Term:02d}\n"
            f"    ➡️ TNA_C_IVA: {self.TNA_C_IVA:.2%}\n"
            f"    ➡️ First_Due_Date: {self.Due_Date}\n"
        )
