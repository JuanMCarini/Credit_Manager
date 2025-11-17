from pandas import DataFrame

from str.database.connection import read_table, write_table
from str.database.structure.clients.tool import validate_cuil
from str.database.structure.lines import Line, search_line_id
from str.tool import _log, log, validate_email


class Organism:
    def _to_dict(self) -> dict:
        return {
            "Name": self.Name,
            "CUIT": self.CUIT,
            "Line_ID": self.Lien_ID,
            "Email": self.Email,
        }

    def _to_dataframe(self) -> DataFrame:
        return DataFrame([self._to_dict()])

    def __init__(
        self,
        Name: str,
        CUIT: str | int,
        Line: int | str | Line,
        Email: str | None = None,
    ) -> None:
        self.Name = str(Name).upper().strip()
        self.CUIT = validate_cuil(CUIT)
        self.Lien_ID = search_line_id(Line)
        self.Email = validate_email(Email)

        table = "organisms"
        df = read_table("organisms")
        if self.CUIT in df["CUIT"].values:
            print("Codear la actualización!!!!")
            _log(f"✅ The CUIT {self.CUIT} already in the database.\n", log)
        else:
            df_new = self._to_dataframe()
            write_table(df_new, table)
            df = read_table(table)
            _log("    ✅ The new organism is added to the database.\n", log)

    def __str__(self) -> str:
        return (
            f"📖 Organism {self.Name}:\n"
            f"     ➡️ CUIT: {self.CUIT}\n"
            f"     ➡️ Line_ID: {self.Lien_ID}\n"
        )


def search_organism_id(organism: str | int | Organism | None) -> int | None:
    if organism is None:
        return None
    else:
        return 1
