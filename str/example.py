# database/create.py.py

from pandas import Period

from str.database.structure import (
    City,
    Client,
    Client_Employment,
    ClientPhones,
    Credit,
    Employer,
    Line,
    Organism,
)
from str.tool import _log, log

new_client = Client(
    "Carini",
    "Juan Martín",
    36329758,
    20363297588,
    "1992/04/01",
    "MASCULINO",
    "CASADO/A",
    City("BAHÍA BLANCA", "BUENOS AIRES", "ARGENTINA"),  # type: ignore
    "",
    None,
    "juanmcarini@gmail.com",
)


new_employer = Employer(
    "Credise S.A.",
    30709706736,
    City("Bahía Blanca", "Buenos Aires", "Argentina"),
    "19 de Mayo 486",
)

clt_employment = Client_Employment(new_employer, new_client, 1.8 * 10**6, "2023/05/01")
new_phone = ClientPhones(
    Client=36329758, Number="+5492914143811", Type="CELULAR", Relationship="PERSONAL"
)

new_line = Line(
    "Mutual Inventada",
    "30-56125789-8",
    "MI",
    "mutual_inventada@inventada.com",
)

new_org = Organism("Este Organismo", "20-12345678-9", "MI", "org@mutual.com")

new_credit = Credit(
    Due_Date=Period("2026/01/28", freq="D"),
    Capital_Requested=100000.0,
    Capital=95000.0,
    Credit_Type="FRANCES",
    Client=36329758,
    Organism="MI",
    Term=12,
    TNA_C_IVA=1.3,
    Emission_Date=Period.now("D"),
)
_log("\n", log)

new_credit = Credit(
    Due_Date=Period("2026/04/28", freq="D"),
    Capital_Requested=1000000.0,
    Capital=100000.0,
    Credit_Type="FRANCES",
    Client=36329758,
    Organism="MI",
    Term=18,
    TNA_C_IVA=1.45,
    Emission_Date=Period("2026/02/01", "D"),
)
_log("\n", log)
