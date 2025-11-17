from pandas import DataFrame

from str.database.connection import read_table, write_table
from str.database.structure.clients.tool import validate_cuil
from str.tool import _log, log, validate_email


class Line:
    def _to_dict(self) -> dict:
        return {
            "Name": self.name,
            "CUIT": self.CUIT,
            "Abbreviation": self.abbreviation,
            "Email": self.email,
            "Active": self.active,
        }

    def _to_dataframe(self) -> DataFrame:
        return DataFrame([self._to_dict()])

    def __init__(
        self, name: str, cuit: str, abbreviation: str, email: str | None = None
    ):
        table = "business_lines"
        self.name = str(name).upper().strip()
        self.CUIT = validate_cuil(cuit)
        self.abbreviation = str(abbreviation).upper().strip()
        self.email = validate_email(email)
        self.active = True

        df = read_table(table, "CUIT")
        if self.CUIT in df.index.values:
            print("Codear la actualización!!!!")
            _log(f"✅ The CUIT {self.CUIT} already in the database.\n", log)
        else:
            df = self._to_dataframe()
            write_table(df, table)
            df = read_table(table, "CUIT")
            _log("    ✅ The new business line is added to the database.\n", log)

        self.ID = df.at[self.CUIT, "ID"]

    def __str__(self) -> str:
        return (
            f"💿 Line ID {self.ID:03d}:\n"
            f"    ➡️ Name: {self.name}\n"
            f"    ➡️ CUIT: {self.CUIT}\n"
            f"    ➡️ Abbreviation: {self.abbreviation}\n"
            f"    ➡️ Email: {self.email}\n"
            f"    ➡️ Active: {self.active}\n"
        )


def search_line_id(line: str | int | Line) -> int:
    table = "business_lines"
    if isinstance(line, Line):
        return line.ID  # type: ignore
    elif isinstance(line, int):
        df = read_table(table)
        if line in df.index.values:
            return line
        else:
            raise ValueError(f"The Line ID {line} is not in the database.")
    elif isinstance(line, str):
        df = read_table(table)
        line = str(line).upper().strip()
        if line in df["Name"].values:
            return df.loc[df["Name"] == line].index.values[0]
        elif line in df["Abbreviation"].values:
            return df.loc[df["Abbreviation"] == line].index.values[0]
        else:
            raise ValueError(f"The Line '{line}' is not in the database.")
    else:
        raise TypeError("The line must be a Line object, an integer ID, or a string.")
