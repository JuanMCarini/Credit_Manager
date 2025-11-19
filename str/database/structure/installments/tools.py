from numpy_financial import ipmt, pmt, ppmt
from pandas import Period

from str.constants import OUR_COMPANY_ID


def inst_french(
    self,
    Credit_ID: int,
    cap: float,
    tna: float,
    term: int,
    i: int,
    first_due_date: Period,
):
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

    return self


def inst_german(
    self,
    cap: float,
    tna: float,
    term: int,
    i: int,
    first_due_date: Period,
    Credit_ID: int,
):
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

    return self


def inst_penalty(
    self,
    cap: float,
    i: int,
    first_due_date: Period,
    Credit_ID: int,
):
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
    return self
