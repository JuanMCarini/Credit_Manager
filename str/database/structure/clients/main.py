from datetime import datetime

from pandas import DataFrame, Period

from str.categories import City, Genders, MaritalStatus
from str.database.connection import read_table, write_table
from str.database.structure.clases import Email
from str.database.structure.clients.tool import validate_dni_cuil
from str.tool import _log, log


class Client:
    def _to_dict(self):
        return {
            "Last_Name": self.Last_Name,
            "First_Name": self.First_Name,
            "DNI": self.DNI,
            "CUIL": self.CUIL,
            "Birth_Date": self.Birth_Date,
            "Gender_ID": self.Gender_ID,
            "Marital_Status_ID": self.Marital_Status_ID,
            "City_ID": self.City_ID,
            "Address": self.Address,
            "Additional_Addresses": self.Additional_Addresses,
            "Email": self.Email,
            "Status_Date": self.Status_Date,
            "Active": self.Active,
        }

    def _to_dataframe(self):
        return DataFrame([self._to_dict()])

    def __init__(
        self,
        Last_Name: str,
        First_Name: str,
        DNI: str | int,
        CUIL: str | int,
        Birth_Date: str | Period | datetime,
        Gender: Genders,
        Marital_Status: MaritalStatus,
        City_: City,
        Address: str,
        Additional_Addresses: str | None,
        Email_Address: str | None,
    ):
        table = "clients"
        DNI, CUIL = validate_dni_cuil(DNI, CUIL)
        df = read_table(table, "CUIL")

        self.Last_Name = Last_Name
        self.First_Name = First_Name
        self.DNI = DNI
        self.CUIL = CUIL
        self.Birth_Date = Birth_Date
        df_genders = read_table("genders", "Description")
        self.Gender_ID = df_genders.at[Gender, "ID"]
        df_martial_status = read_table("marital_status", "Description")
        self.Marital_Status_ID = df_martial_status.at[Marital_Status, "ID"]
        self.City_ID = City_.ID  # type: ignore
        self.Address = Address
        self.Additional_Addresses = Additional_Addresses
        self.Email = Email(Email_Address).address
        self.Status_Date = Period.now("D")
        self.Active = True

        if (CUIL not in df.index.values) and (DNI not in df["DNI"].values):
            _log("\n✏️ Adding a new client...", log)
            df = self._to_dataframe()
            write_table(df, table)
            df = read_table(table, "CUIL")
            _log("    ✅ The new client is added to the database.\n", log)
        else:
            print("Codear la actualización!!!!")
            _log(
                f"✅ The CUIL {CUIL} and the DNI {DNI} already in the database.\n", log
            )
        self.ID: int = df.at[CUIL, "ID"]  # type: ignore

    def __str__(self):
        """
        --------------------------------------------------------
          STRING REPRESENTATION — CLIENT
        --------------------------------------------------------
          Returns a readable summary of the client, converting
          foreign keys (Gender, Marital Status, City) into their
          human-friendly descriptions.
        --------------------------------------------------------
        """
        # --- Load descriptive values ---
        df_genders = read_table("genders")
        gender_desc = df_genders.at[self.Gender_ID, "Description"]  # type: ignore

        df_marital = read_table("marital_status")
        marital_desc = df_marital.at[self.Marital_Status_ID, "Description"]  # type: ignore

        df_cities = read_table("cities")
        df_provinces = read_table("provinces")
        df_countries = read_table("countries")

        city_name = df_cities.at[self.City_ID, "Name"]
        province_id = df_cities.at[self.City_ID, "Province_ID"]
        province_name = df_provinces.at[province_id, "Name"]  # type: ignore
        country_id = df_provinces.at[province_id, "Country_ID"]  # type: ignore
        country_name = df_countries.at[country_id, "Name"]  # type: ignore

        # --- Format output ---
        return (
            f"\n🧍 CLIENT #{self.ID:06d}\n"
            f"    ➡️ Name: {self.First_Name} {self.Last_Name}\n"
            f"    ➡️ DNI / CUIL: {self.DNI} / {self.CUIL}\n"
            f"    ➡️ Birth Date: {self.Birth_Date}\n"
            f"    ➡️ Gender: {gender_desc}\n"
            f"    ➡️ Marital Status: {marital_desc}\n"
            f"    ➡️ Location: {city_name}, {province_name}, {country_name}\n"
            f"    ➡️ Address: {self.Address}\n"
            f"    ➡️ Additional Addresses: {self.Additional_Addresses}\n"
            f"    ➡️ Email: {self.Email}\n"
            f"    ➡️ Status Date: {self.Status_Date}\n"
            f"    ➡️ Active: {self.Active}"
        )
