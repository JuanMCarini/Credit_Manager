from enum import StrEnum

import numpy_financial as npf
import pandas as pd

import str.tool as tool
from str.database.connection import engine
from str.database.create import OUR_COMPANY_ID, Credit_Types


class Gender(StrEnum):
    NO_BINARIO = ("No Binario", 1)
    MASCULINO = ("Masculino", 2)
    FEMENINO = ("Femenino", 3)
    OTRO = ("Otro", 4)

    def __new__(cls, label: str, db_id: int):
        obj = str.__new__(cls, label)
        obj._value_ = label
        obj.ID = db_id  # type: ignore
        return obj


class Marital_Status(StrEnum):
    SOLTERO = ("Soltero", 1)
    CASADO = ("Casado", 2)
    VIUDO = ("Viudo", 3)
    DIVORCIADO = ("Divorciado", 4)
    SEPARADO = ("Separado", 5)
    CONVIVIENTE = ("Conviviente", 6)
    DESCONOCIDO = ("Desconocido", 7)

    def __new__(cls, label: str, db_id: int):
        obj = str.__new__(cls, label)
        obj._value_ = label
        obj.ID = db_id  # type: ignore
        return obj


class Business_Partner:
    def __init__(self, ID: int, Name: str, CUIL: str, Email: str, Active: bool):
        self.ID = ID
        self.Name = Name
        self.CUIL = CUIL
        self.Email = Email
        self.Active = Active

    def __str__(self):
        return f"Datos de empresa la {str(self.ID).zfill(2)} - {self.Name},\n   -> CUIL: {self.CUIL},\n   -> Email: {self.Email},\n   -> Activo: {self.Active == 1}"

    def cambiar_estado(self):
        if self.Active:
            self.Active = False
        else:
            self.Active = True


class Client:
    def __init__(
        self,
        ID,
        Last_Name,
        First_Name,
        DNI,
        CUIL,
        Birth_Date,
        Gender_ID,
        Marital_Status_ID,
        Nationality_ID,
        Province_ID,
        City_ID,
        Address,
        Email,
    ):
        self.ID = ID
        self.Last_Name = Last_Name
        self.First_Name = First_Name
        self.CUIL = CUIL
        CUIL = str(CUIL).strip()
        for ch in ["-", "/", " "]:
            CUIL = CUIL.replace(ch, "")
        if not tool.validar_cuit_cuil(CUIL):
            raise ValueError(f"{CUIL} no es un CUIL.")
        else:
            CUIL = int(CUIL)
            if not (int(DNI) == CUIL // 10 % 10**8):
                raise ValueError(f"El DNI ({DNI}) no coincide con el CUIL ({CUIL}).")
        self.DNI = DNI
        self.Birth_Date = pd.Period(Birth_Date, freq="D")
        self.Gender_ID = Gender_ID
        self.Marital_Status_ID = Marital_Status_ID
        self.Nationality_ID = Nationality_ID
        self.Province_ID = Province_ID
        self.City_ID = City_ID
        self.Address = Address
        self.Email = Email
        self.Status_Date = pd.Period.now("D")
        self.Active = True

    def update(self):
        self.Status_Date = pd.Period.now("D")

    def cambiar_estado(self):
        self.Active = not self.Active
        self.update()

    def to_dict(self):
        return {
            "ID": self.ID,
            "Last_Name": self.Last_Name,
            "First_Name": self.First_Name,
            "DNI": self.DNI,
            "CUIL": self.CUIL,
            "Birth_Date": self.Birth_Date,
            "Gender_ID": self.Gender_ID,
            "Marital_Status_ID": self.Marital_Status_ID,
            "Nationality_ID": self.Nationality_ID,
            "Province_ID": self.Province_ID,
            "City_ID": self.City_ID,
            "Address": self.Address,
            "Email": self.Email,
            "Status_Date": self.Status_Date,
            "Active": self.Active,
        }

    def __str__(self):
        return f"Client {self.ID:05d} – {self.Last_Name}, {self.First_Name} | Active={self.Active}"


class CreditType(StrEnum):
    FRANCES = ("Frances", 1)
    ALEMAN = ("Aleman", 2)

    def __new__(cls, label: str, db_id: int):
        obj = str.__new__(cls, label)
        obj._value_ = label
        obj.ID = db_id  # type: ignore
        return obj


def installment_values(
    Capital: float,
    TNA_C_IVA: float,
    Term: int,
    credit_type: CreditType,
    Nro_Cta: int = 0,
) -> tuple[float, float, float, float]:
    r = TNA_C_IVA / 365 * 30
    if Nro_Cta not in [i + 1 for i in range(Term)]:
        raise ValueError(
            f"{Nro_Cta} no es una número de cuota valido para el plazo {Term}."
        )
    elif credit_type == CreditType.FRANCES:
        inst = float(npf.pmt(r, Term, -Capital, 0))
        interest = float(npf.ipmt(r, Nro_Cta, Term, -Capital, 0))
        capital = inst - interest
        interest = interest / 1.21
        iva = inst - (capital + interest)

    elif credit_type == CreditType.ALEMAN:
        capital = Capital / Term
        res_cap = Capital - capital * (Nro_Cta - 1)
        interest = res_cap * r
        iva = interest / 1.21 * 0.21
        inst = capital + interest + iva

    else:
        raise ValueError(f"{credit_type} no es un tipo de crédito valido")

    return capital, interest, iva, inst


def installments(
    Capital: float,
    TNA_C_IVA: float,
    Term: int,
    credit_type: CreditType,
    first_due: pd.Period,
) -> pd.DataFrame:
    df = []
    due_day = int(first_due.day)
    for i in range(1, Term + 1):
        vto = pd.Period(first_due, freq="M") + i - 1
        vto = pd.Period(year=vto.year, month=vto.month, day=due_day, freq="D")
        capital, interest, iva, inst = installment_values(
            Capital, TNA_C_IVA, Term, credit_type, i
        )
        df.append(
            {
                "Inst_Num": i,
                "Capital": capital,
                "Interest": interest,
                "IVA": iva,
                "Total": inst,
                "Due_Date": vto,
            }
        )
    df = pd.DataFrame(df)

    return df


class Credit:
    def to_dict(self):
        return {
            "Origin_ID": self.Origin_ID,
            "Disbursement_Date": self.Disbursement_Date,
            "First_Due_Date": self.First_Due_Date,
            "Amount_Disbursed": self.Amount_Disbursed,
            "Capital": self.Capital,
            "Credit_Type_ID": self.Credit_Type_ID,
            "TNA_C_IVA": self.TNA_C_IVA,
            "Term": self.Term,
            "Client_ID": self.Client_ID,
            "Organism_ID": self.Organism_ID,
            "Purchase_ID": self.Purchase_ID,
            "Sale_ID": self.Sale_ID,
        }

    def to_database(self):
        pd.DataFrame([self.to_dict()]).to_sql(
            "credits", engine, index=False, if_exists="append"
        )

    def __init__(
        self,
        Origin_ID: int | str | None,
        Amount_Disbursed: float,
        Capital: float,
        Credit_Type: CreditType,
        TNA_C_IVA: float,
        Term: int,
        Client_ID: int,
        Organism_ID: int,
        Disbursement_Date: str | pd.Period = pd.Period.now("D"),
        Grace: int = 0,
        Due_Day: int = 28,
        Purchase_ID: int | None = None,
        Sale_ID: int | None = None,
    ):
        def first_due(
            date: str | pd.Period, grace: int = 0, due_day: int = 28
        ) -> pd.Period:
            date = pd.Period(date, freq="M") + grace

            return pd.Period(year=date.year, month=date.month, day=due_day, freq="D")

        self.Origin_ID = Origin_ID
        self.Disbursement_Date = pd.Period(Disbursement_Date, freq="D")
        self.First_Due_Date = first_due(Disbursement_Date, Grace, Due_Day)
        self.Amount_Disbursed = Amount_Disbursed
        self.Capital = Capital
        self.Credit_Type_ID = Credit_Type.ID  # type: ignore
        self.TNA_C_IVA = TNA_C_IVA
        self.Term = Term
        df_clts = pd.read_sql("clients", engine, index_col="ID")
        if Client_ID in df_clts.index:
            self.Client_ID = Client_ID
        else:
            raise ValueError(f"{Client_ID} no es el ID de un cliente.")
        df_org = pd.read_sql("organisms", engine, index_col="ID")
        if Organism_ID in df_org.index:
            self.Organism_ID = Organism_ID
        else:
            raise ValueError(f"{Organism_ID} no es el ID de un organismo.")
        df_purch = pd.read_sql("purchases", engine, index_col="ID")
        if (Purchase_ID in df_purch.index) or (Purchase_ID is None):
            self.Purchase_ID = Purchase_ID
        else:
            raise ValueError(f"{Purchase_ID} no es el ID de un compra de cartera.")
        df_sales = pd.read_sql("sales", engine, index_col="ID")
        if (Sale_ID in df_sales.index) or (Sale_ID is None):
            self.Sale_ID = Sale_ID
        else:
            raise ValueError(f"{Sale_ID} no es el ID de una venta de cartera.")

        self.to_database()
        self.ID = pd.read_sql("credits", engine, index_col="ID").index.max()

        df_inst = installments(
            self.Capital, self.TNA_C_IVA, self.Term, Credit_Type, self.First_Due_Date
        )
        df_inst["Credit_ID"] = self.ID
        df_inst["Owner_ID"] = OUR_COMPANY_ID
        df_inst["Settlement_Date"] = df_inst["Due_Date"]
        df_inst.to_sql("installments", engine, index=False, if_exists="append")

    def __str__(self):
        if self.Credit_Type_ID == Credit_Types.at["FRANCES", "ID"]:
            Credit_Type = CreditType.FRANCES
        elif self.Credit_Type_ID == Credit_Types.at["ALEMAN", "ID"]:
            Credit_Type = CreditType.ALEMAN

        return f"""Crédito Nro. {self.ID:07d}:
    -> ID Original: {self.Origin_ID:07d}
    -> Emisión: {self.Disbursement_Date}
    -> Capital: $ {self.Capital:,.2f}
    -> Tipo de Crédito: {str(Credit_Type).title()}
    -> TNA c/IVA: {self.TNA_C_IVA:.2%}
    -> Plazo: {self.Term}
    -> Primer Vto.: {self.First_Due_Date}"""
