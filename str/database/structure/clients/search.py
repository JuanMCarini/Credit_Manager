# database/structure/clients/search.py

from str.database.connection import read_table
from str.database.structure.clients import Client
from str.database.structure.clients.tool import validate_cuil


def search_id(value: int | str | Client) -> int:
    """
    Given:
      - a Client instance  -> returns its ID
      - a DNI (int or str) -> looks up by DNI in 'clients' table
      - a CUIL/CUIT (int or str) -> looks up by CUIL in 'clients' table

    Raises:
      ValueError if the value doesn't look like DNI/CUIL
      KeyError if DNI/CUIL is not found in the table
    """

    # 1) If it's already a Client, life is easy
    if isinstance(value, Client):
        return value.ID

    # 2) Normalize to string for analysis
    text = str(value).strip()

    # Extract only digits (handles '20-36329758-8', '  38522111 ', etc.)
    digits = "".join(ch for ch in text if ch.isdigit())

    # If it has letters, we treat it as "name-like" and reject
    if any(ch.isalpha() for ch in text):
        raise ValueError(
            f"Expected DNI/CUIL or Client instance, but got a name-like value: {value!r}"
        )

    if not digits:
        raise ValueError(
            f"Could not extract any digits from {value!r}. Expected DNI or CUIL."
        )

    # 3) DNI: usually 7 or 8 digits
    if len(digits) in (7, 8):
        dni = int(digits)
        df = read_table("clients", "DNI")
        if dni not in df.index:
            raise KeyError(f"DNI {dni} not found in 'clients' table.")
        return int(df.at[dni, "ID"])  # type: ignore

    # 4) CUIL/CUIT: 11 digits + validation
    if len(digits) == 11:
        cuil = validate_cuil(digits)  # assume this returns normalized CUIL
        df = read_table("clients", "CUIL")
        if cuil not in df.index:
            raise KeyError(f"CUIL {cuil} not found in 'clients' table.")
        return int(df.at[cuil, "ID"])  # type: ignore

    # 5) Anything else: doesn't match DNI or CUIL
    raise ValueError(
        f"Value {value!r} does not look like a valid DNI (7–8 digits) "
        f"or CUIL/CUIT (11 digits)."
    )
