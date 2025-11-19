from pandas import DataFrame, Period

from str.database.connection import read_table, write_table
from str.database.structure.installments.tools import (
    inst_french,
    inst_german,
    inst_penalty,
)
from str.tool import _log, log


class Installment:
    def _to_dict(self) -> dict:
        return {
            "Credit_ID": self.Credit_ID,  # type: ignore
            "Inst_Num": self.Inst_Num,  # type: ignore
            "Owner_ID": self.Owner_ID,  # type: ignore
            "Due_Date": self.Due_Date,  # type: ignore
            "Capital": self.Capital,  # type: ignore
            "Interest": self.Interest,  # type: ignore
            "IVA": self.IVA,  # type: ignore
            "Total": self.Total,  # type: ignore
            "Settlement_Date": self.Settlement_Date,  # type: ignore
        }

    def _to_dataframe(self) -> DataFrame:
        return DataFrame([self._to_dict()])

    def __init__(self, Credit_ID: int, i: int):
        df_crts = read_table("credits")
        df_crtp = read_table("credit_types")
        data = df_crts.loc[Credit_ID]
        cap = float(data["Capital"])  # type: ignore
        tna = float(data["TNA_C_IVA"])  # type: ignore
        term = int(data["Term"])  # type: ignore
        id_credit_type = int(data["Credit_Type_ID"])  # type: ignore
        first_due_date = Period(data["First_Due_Date"], freq="M")  # type: ignore
        df = []
        if df_crtp.at[id_credit_type, "Name"] == "FRANCES":
            self = inst_french(
                self,
                Credit_ID=Credit_ID,
                cap=cap,
                tna=tna,
                term=term,
                i=i,
                first_due_date=first_due_date,
            )
        elif df_crtp.at[id_credit_type, "Name"] == "ALEMAN":
            self = inst_german(
                self,
                cap=cap,
                tna=tna,
                term=term,
                i=i,
                first_due_date=first_due_date,
                Credit_ID=Credit_ID,
            )
        elif df_crtp.at[id_credit_type, "Name"] == "PENALTY":
            self = inst_penalty(
                self,
                cap=cap,
                i=i,
                first_due_date=first_due_date,
                Credit_ID=Credit_ID,
            )
        else:
            raise ValueError(
                f"❌ Credit Type {df_crtp.at[id_credit_type, 'Name']} not implemented."
            )

        df = read_table("installments")
        if (Credit_ID in df["Credit_ID"].values) and (
            i in df.loc[(df["Credit_ID"] == Credit_ID), "Inst_Num"].values
        ):
            mask = (df["Credit_ID"] == Credit_ID) & (df["Inst_Num"] == i)
            df_exist = df.loc[mask]
            if df_exist.empty:
                raise ValueError(
                    f"❌ Installment {i} for Credit_ID {Credit_ID} not found in database."
                )
            elif len(df_exist) > 1:
                raise ValueError(
                    f"❌ Multiple installments {i} for Credit_ID {Credit_ID} found in database."
                )
            else:
                self.ID = int(df_exist.index.values[0])
        else:
            df = self._to_dataframe()
            write_table(df, "installments")
            df = read_table("installments")
            self.ID = int(df.index.values.max())
            _log(
                f"✅ Installment {i:02d} of {term:02d} for Credit_ID {Credit_ID:08d} created with ID {self.ID}.",
                log,
            )
