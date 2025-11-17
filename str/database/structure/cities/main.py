from str.database.connection import read_table, write_table
from str.database.structure.countries import Country
from str.database.structure.provinces import Province
from str.tool import _log, log


class City:
    """
    ============================================================
      CITY CLASS
    ------------------------------------------------------------
      Represents a city and ensures it exists in the SQL table.
      - Validates or creates its province.
      - Automatically links to the correct country.
    ============================================================
    """

    def __init__(self, name: str, province: str, country: str | None = None):
        """
        --------------------------------------------------------
          CONSTRUCTOR
        --------------------------------------------------------
          Creates or retrieves a city.

          Steps:
          1. Normalize inputs.
          2. Ensure the province exists (create if needed).
          3. Insert the city if missing.
          4. Load the City ID into the instance.
        --------------------------------------------------------
        """

        # ---------- Normalize ----------
        name = str(name).upper().strip()
        province = str(province).upper().strip()
        table = "cities"

        self.Name = name  # city name stored in instance

        # ---------- Load tables ----------
        df = read_table(table)
        df_provinces = read_table("provinces")
        df_countries = read_table("countries", "Name")

        # Ask for country if missing
        if country is None:
            country = input("Ingrese el país donde está la ciudad: ")
        country = str(country).upper().strip()

        if country in df_countries.index.values:
            country_id = df_countries.at[country, "ID"]
        else:
            new_country = Country(country)
            country_id = new_country.ID

        # ---------- Province exists with this country? ----------
        mask = (df_provinces["Name"] == province) & (
            df_provinces["Country_ID"] == country_id
        )
        if len(df_provinces.loc[mask]) == 1:
            row = df_provinces.loc[mask]
            self.Province_ID = int(row.index[0])  # take scalar, not Series
        elif len(df_provinces.loc[mask]) > 1:
            raise ValueError(
                f"The province {province} in the country {country} is repeat."
            )
        else:
            # Create province → will also create country if needed
            print(province, country)
            new_province = Province(province, country)
            print(new_province)
            self.Province_ID = new_province.ID

        # ---------- Insert new city ----------
        if name not in df.loc[df["Province_ID"] == self.Province_ID, "Name"].values:
            _log("\n✏️ Adding a new city...", log)

            df = df.iloc[0:0]  # empty frame to insert
            df.loc[0] = {
                "Name": self.Name,
                "Province_ID": self.Province_ID,  # FK to provinces table
            }

            write_table(df, table)
            _log(f"    ✅ {name} added to the database.\n", log)

        # ---------- City already exists ----------
        else:
            _log(f"✅ {name} already in the database.\n", log)

        # Reload indexed by Name for lookup
        df = read_table(table, "Name")
        self.ID = df.at[self.Name, "ID"]  # store City ID

    def __str__(self):
        """
        --------------------------------------------------------
          STRING REPRESENTATION
        --------------------------------------------------------
          Shows city name, its province and its country.
        --------------------------------------------------------
        """
        df_provinces = read_table("provinces")
        df_countries = read_table("countries")

        province_name = df_provinces.at[self.Province_ID, "Name"]  # type: ignore
        country_name = df_countries.at[
            df_provinces.at[self.Province_ID, "Country_ID"], "Name"  # type: ignore
        ]

        return (
            f"\nℹ️ City ID: {self.ID:03d}\n"
            f"    ➡️ Name: {self.Name}\n"
            f"    ➡️ Province: {province_name}\n"
            f"    ➡️ Country: {country_name}\n"
        )
