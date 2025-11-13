from str.database.connection import read_table, write_table
from str.database.structure.countries import Country
from str.tool import _log, log


class Province:
    """
    ============================================================
      PROVINCE CLASS
    ------------------------------------------------------------
      Handles creation, lookup and representation of provinces.
      Each province belongs to a country, linked by Country_ID.
    ============================================================
    """

    def __init__(self, name: str, country: str):
        """
        --------------------------------------------------------
          CONSTRUCTOR
        --------------------------------------------------------
          Creates (or retrieves) a province.

          - Normalizes inputs.
          - Ensures the country exists (creates it if needed).
          - Inserts the province if missing.
          - Loads ID and Country_ID for the instance.
        --------------------------------------------------------
        """

        name = str(name).upper().strip()  # normalize province name
        country = str(country).upper().strip()  # normalize country name
        table = "provinces"

        self.Name = name  # store province name

        # Load existing provinces and countries
        df = read_table(table)
        df_country = read_table("countries", "Name")

        # ---------- COUNTRY HANDLING ----------
        if country in df_country.index.values:
            self.Country_ID = df_country.at[country, "ID"]  # existing country
        else:
            new_country = Country(country)  # create new country
            self.Country_ID = new_country.ID  # assign new ID

        # ---------- PROVINCE DOES NOT EXIST ----------
        if name not in df.loc[df["Country_ID"] == self.Country_ID, "Name"].values:
            _log("\n✏️ Adding a new province...", log)

            df = df.iloc[0:0]  # empty df to insert row
            df.loc[0] = {
                "Name": self.Name,
                "Country_ID": self.Country_ID,  # FK to countries table
            }

            write_table(df, table)
            _log(f"    ✅ {name} added to the database.\n", log)

        # ---------- PROVINCE ALREADY EXISTS ----------
        else:
            _log(f"✅ {name} already in the database.\n", log)

        # Load indexed by Name for fast lookup
        df = read_table(table, "Name")
        mask = (df.index == self.Name) & (df["Country_ID"] == self.Country_ID)

        if len(df.loc[mask, "ID"]) == 1:
            self.ID = df.loc[mask, "ID"].values[0]  # assign Province ID
        else:
            raise ValueError(
                f"More than one province named {self.Name} in the country {country}"
            )

    def __str__(self):
        """
        --------------------------------------------------------
          STRING REPRESENTATION
        --------------------------------------------------------
          Returns a human-readable description of the province,
          including the name of its associated country.
        --------------------------------------------------------
        """

        df_countries = read_table("countries")  # load for lookup
        country_name = df_countries.at[self.Country_ID, "Name"]  # type: ignore
        try:
            return (
                f"\nℹ️ Province ID: {self.ID:03d}\n"
                f"    ➡️ Name: {self.Name}\n"
                f"    ➡️ Country: {country_name}\n"
            )
        except TypeError:
            print(self.ID)
