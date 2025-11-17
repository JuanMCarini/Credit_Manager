from numpy_financial import ipmt, pmt, ppmt
from pandas import DataFrame, Period

from str.constants import OUR_COMPANY_ID
from str.database.connection import read_table, write_table
from str.tool import _log, log


class Installment:
    def _to_dict(self) -> dict:
        return {
            "Credit_ID": self.Credit_ID,
            "Inst_Num": self.Inst_Num,
            "Owner_ID": self.Owner_ID,
            "Due_Date": self.Due_Date,
            "Capital": self.Capital,
            "Interest": self.Interest,
            "IVA": self.IVA,
            "Total": self.Total,
            "Settlement_Date": self.Settlement_Date,
        }

    def _to_dataframe(self) -> DataFrame:
        return DataFrame([self._to_dict()])

    def __init__(self, Credit_ID: int, i: int):
        df_crts = read_table("credits")
        df_crtp = read_table("credit_types")
        data = df_crts.loc[Credit_ID]
        cap = data["Capital"]
        tna = data["TNA_C_IVA"]
        term = int(data["Term"])  # type: ignore
        id_credit_type = int(data["Credit_Type_ID"])  # type: ignore
        first_due_date = Period(data["First_Due_Date"], freq="M")  # type: ignore
        df = []
        if df_crtp.at[id_credit_type, "Name"] == "FRANCES":
            inst_value = pmt(rate=tna / 365 * 30, nper=term, pv=-cap)
            inst_cap = ppmt(rate=tna / 365 * 30, per=i, nper=term, pv=-cap)
            inst_int = ipmt(rate=tna / 365 * 30, per=i, nper=term, pv=-cap) / 1.21
            inst_iva = inst_value - (inst_cap + inst_int)
            vto_date = Period(first_due_date + (i - 1))
            vto_date = Period(f"{vto_date.year}/{vto_date.month}/28", freq="D")
            self.Credit_ID = Credit_ID
            self.Inst_Num = i
            self.Owner_ID = OUR_COMPANY_ID
            self.Due_Date = vto_date
            self.Capital = inst_cap
            self.Interest = inst_int
            self.IVA = inst_iva
            self.Total = inst_value
            self.Settlement_Date = vto_date
        elif df_crtp.at[id_credit_type, "Name"] == "ALEMAN":
            inst_cap = cap / term
            inst_int = (cap - inst_cap * (i - 1)) * (tna / 365 * 30) / 1.21
            inst_iva = inst_int * 0.21
            inst_value = inst_cap + inst_int + inst_iva
            vto_date = Period(first_due_date + (i - 1))
            vto_date = Period(f"{vto_date.year}/{vto_date.month}/28", freq="D")
            self.Credit_ID = Credit_ID
            self.Inst_Num = i
            self.Owner_ID = OUR_COMPANY_ID
            self.Due_Date = vto_date
            self.Capital = inst_cap
            self.Interest = inst_int
            self.IVA = inst_iva
            self.Total = inst_value
            self.Settlement_Date = vto_date
        elif df_crtp.at[id_credit_type, "Name"] == "PENALTY":
            inst_cap = 0.0
            inst_int = cap / 1.21
            inst_iva = cap - inst_int
            inst_value = cap
            vto_date = Period(first_due_date + (i - 1))
            vto_date = Period(f"{vto_date.year}/{vto_date.month}/28", freq="D")
            self.Credit_ID = Credit_ID
            self.Inst_Num = i
            self.Owner_ID = OUR_COMPANY_ID
            self.Due_Date = vto_date
            self.Capital = inst_cap
            self.Interest = inst_int
            self.IVA = inst_iva
            self.Total = inst_value
            self.Settlement_Date = vto_date
        else:
            raise ValueError(
                f"❌ Credit Type {df_crtp.at[id_credit_type, 'Name']} not implemented."
            )

        df = read_table("installments")
        if (Credit_ID in df["Credit_ID"].values) and (i in df["Inst_Num"].values):
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
