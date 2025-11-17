import pandas as pd

from str.database.connection import read_table, write_table
from str.database.structure import City, search_city_id
from str.database.structure.clients.tool import validate_cuil
from str.database.structure.organisms import search_organism_id


class Employer:
    """
    Represents an employer stored in the `employers` table.

    Responsibilities:
      - Normalize and validate employer data (CUIT, city, address).
      - Insert the employer into the database if it does not exist.
      - Retrieve and expose the employer's database ID if it already exists.
    """

    def _to_dict(self) -> dict:
        """Return the employer data as a plain dictionary, ready for DataFrame insertion."""
        return {
            "Employer": self.Employer,
            "CUIT": self.CUIT,
            "City_ID": self.City_ID,
            "Address": self.Address,
            "Organism_ID": self.Organism_ID,
        }

    def _to_dataframe(self) -> pd.DataFrame:
        """Return the employer data as a single-row DataFrame."""
        return pd.DataFrame([self._to_dict()])

    def __init__(
        self,
        Name: str,
        CUIT: str | int,
        City: City,
        Address: str | None,
        Organism: str | None = None,
    ):
        """
        Create (or load) an employer from the `employers` table.

        If the CUIT already exists in the table:
          - Load its ID from the database.

        If the CUIT does not exist:
          - Insert a new row with the given data.
          - Reload the table and set the ID accordingly.
        """

        table = "employers"

        # Normalize / validate attributes
        self.Employer = str(Name).strip()
        self.CUIT = validate_cuil(
            CUIT
        )  # assume this returns a normalized CUIT (string or int)
        self.City_ID = search_city_id(City)
        self.Address = None if Address is None else str(Address).strip()
        self.Organism_ID = search_organism_id(Organism)
        # Read current employers indexed by CUIT
        df = read_table(table, index_col="CUIT")

        if self.CUIT in df.index.values:
            # Employer already exists → get its ID
            self.ID = df.at[self.CUIT, "ID"]
        else:
            # Employer does not exist → insert and reload
            new_row = self._to_dataframe()
            write_table(new_row, table)
            df = read_table(table, index_col="CUIT")
            self.ID = df.at[self.CUIT, "ID"]

    def __str__(self) -> str:
        """Human-readable representation of the employer."""
        return f"🗃️ Employer (ID {self.ID:02d}):\n    ➡️ Name: {self.Employer},\n    ➡️ CUIT: {self.CUIT}"


def get_employer_id(employer: int | str | Employer):
    """
    Returns the Employer ID from one of three input types:
    - int: treated as a CUIT
    - str: treated as employer name
    - Employer instance: takes ID directly
    """

    if isinstance(employer, int):
        cuit = validate_cuil(employer)
        df = read_table("employers", "CUIT")
        return df.at[cuit, "ID"]

    elif isinstance(employer, str):
        df = read_table("employers", "Employer")
        return df.at[employer.upper().strip(), "ID"]

    elif isinstance(employer, Employer):
        return employer.ID

    else:
        raise TypeError(
            f"Invalid type for employer: {type(employer).__name__}. "
            f"Expected int, str, or Employer instance."
        )
