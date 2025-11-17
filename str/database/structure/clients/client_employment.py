from datetime import datetime

from pandas import DataFrame, Period

from str.database.connection import read_table, write_table
from str.database.structure import Client, Employer, get_employer_id, search_client_id


class Client_Employment:
    def _to_dict(self):
        return {
            "Employer_ID": self.Employer_ID,
            "Client_ID": self.Client_ID,
            "Monthly_Income": self.Income,
            "Start_Date": self.Start,
            "End_Date": self.End,
        }

    def _to_dataframe(self):
        return DataFrame([self._to_dict()])

    def __init__(
        self,
        employer: str | int | Employer,
        Client: str | int | Client,
        Monthly_Income: float,
        Start_Date: str | Period | datetime,
        End_Date: str | Period | datetime | None = None,
    ):
        table = "employers_clients"
        self.Employer_ID = get_employer_id(employer)
        self.Client_ID = search_client_id(Client)
        self.Income = Monthly_Income
        self.Start = Start_Date
        self.End = End_Date

        df = read_table(table)
        mask = (df["Employer_ID"] == self.Employer_ID) & (
            df["Client_ID"] == self.Client_ID
        )
        if df.loc[mask].empty:
            df = self._to_dataframe()
            write_table(df, table)
            df = read_table(table)
            mask = (df["Employer_ID"] == self.Employer_ID) & (
                df["Client_ID"] == self.Client_ID
            )
        else:
            print("Codear la actualización!!!!")

        if len(df.loc[mask]) == 1:
            self.ID = df.loc[mask].index.values[0]
        else:
            raise ValueError("Gandalf fill")

    def __str__(self):
        df_clients = read_table("clients")
        last_name = df_clients.at[self.Client_ID, "Last_Name"]
        first_name = df_clients.at[self.Client_ID, "First_Name"]
        CUIL = df_clients.at[self.Client_ID, "CUIL"]
        df_employers = read_table("employers")
        employer = df_employers.at[self.Employer_ID, "Employer"]  # type: ignore
        return f"El empleado {last_name}, {first_name} (CUIL {CUIL}), trabaja en {employer}{'.' if not str(employer).endswith('.') else ''}"
