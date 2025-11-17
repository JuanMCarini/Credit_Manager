from pandas import DataFrame

from str.categories import PhoneTypes, RelationshipsTypes
from str.database.connection import read_table, write_table
from str.database.structure import Client, search_client_id


class ClientPhones:
    def _to_dict(self):
        return {
            "Client_ID": self.client_id,
            "Number": self.Number,
            "Type_ID": self.Type_ID,
            "Relationship_ID": self.Relationship_ID,
        }

    def _to_dataframe(self):
        return DataFrame([self._to_dict()])

    def __init__(
        self,
        Client: str | int | Client,
        Number: str | int,
        Type: PhoneTypes,
        Relationship: RelationshipsTypes,
    ):
        self.client_id = search_client_id(Client)
        self.Number = Number
        df_phone_types = read_table("phone_types", "Name")
        df_relationships = read_table("relationships", "Name")
        self.Type_ID = df_phone_types.at[Type, "ID"]
        self.Relationship_ID = df_relationships.at[Relationship, "ID"]

        table = "phones"
        df = read_table(table)
        new_phone = self._to_dataframe()
        mask = (df["Client_ID"] == self.client_id) & (df["Number"] == self.Number)
        if df.loc[mask].empty:
            write_table(new_phone, table)
            df = read_table(table)
            mask = (df["Client_ID"] == self.client_id) & (df["Number"] == self.Number)
            self.ID = df.loc[mask].index[0]
        else:
            self.ID = df.loc[mask].index[0]

    def __str__(self):
        return f"📞 Phone(ID={self.ID}, Client={self.client_id}, Number={self.Number})"
