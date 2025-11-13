from str.database.connection import read_table, write_table
from str.tool import _log, log


class Country:
    """
    ============================================================
      COUNTRY CLASS
    ------------------------------------------------------------
      Handles creation, lookup, and display of country records
      stored in the SQL table "countries".
    ============================================================
    """

    def __init__(self, name: str, nationality: str | None = None):
        """
        --------------------------------------------------------
          CONSTRUCTOR
        --------------------------------------------------------
          Creates a Country instance.
          - If the country name does not exist in the database,
            it asks (or receives) the nationality and inserts it.
          - If it exists, it simply loads the stored nationality
            and ID from the table.
        --------------------------------------------------------
        """

        table = "countries"  # target SQL table
        df = read_table(table)  # load table into df

        # Normalize the given name
        name = str(name).upper().strip()

        # ========== Country NOT in database ==========
        if name not in df["Name"].values:
            _log("\n✏️ Adding a new country...", log)

            df = df.iloc[0:0]  # empty frame for insertion
            self.Name = name  # store normalized name

            # Nationality from parameter or user input
            self.Nationality = (
                input("Ingrese la nacionalidad: ").upper().strip()
                if nationality is None
                else str(nationality).upper().strip()
            )

            # Insert row
            df.loc[0] = {"Name": self.Name, "Nationality": self.Nationality}

            write_table(df, table)  # write into SQL
            df = read_table(table, "Name")  # reload indexed by Name

            _log(f"    ✅ {name} added to the database.\n", log)

        # ========== Country already exists ==========
        else:
            _log(f"\n✅ {name} already in the database.\n", log)

            df = read_table(table, "Name")  # reload indexed by Name
            self.Name = name  # keep normalized
            self.Nationality = df.at[name, "Nationality"]  # read stored value

        # Always retrieve ID at the end
        self.ID = df.at[name, "ID"]  # load SQL ID

    def __str__(self):
        """
        --------------------------------------------------------
          STRING REPRESENTATION
        --------------------------------------------------------
          Returns a printable formatted summary of the country.
        --------------------------------------------------------
        """
        return (
            f"\nℹ️ Country ID: {self.ID:03d}\n"
            f"    ➡️ Name: {self.Name}\n"
            f"    ➡️ Nationality: {self.Nationality}\n"
        )
