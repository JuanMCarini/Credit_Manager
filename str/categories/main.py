# categories.py
from __future__ import annotations

from typing import Literal

Genders = Literal["NO BINARIO", "MASCULINO", "FEMENINO", "OTRO"]
GENDERS: tuple[Genders, ...] = ("NO BINARIO", "MASCULINO", "FEMENINO", "OTRO")

MaritalStatus = Literal[
    "SOLTERO/A", "CASADO/A", "VIUDO/A", "DIVORCIADO/A", "CONVIVIENTE", "DESCONOCIDO"
]
MARITAL_STATUS: tuple[MaritalStatus, ...] = (
    "SOLTERO/A",
    "CASADO/A",
    "VIUDO/A",
    "DIVORCIADO/A",
    "CONVIVIENTE",
    "DESCONOCIDO",
)

CreditTypes = Literal["FRANCES", "ALEMAN", "PENALTY"]
CREDIT_TYPES: tuple[CreditTypes, ...] = ("FRANCES", "ALEMAN", "PENALTY")

CollectionTypes = Literal["COMUN", "ANTICIPADA", "BONIFICACION", "PENALTY", "REDONDEO"]
COLLECTION_TYPES: tuple[CollectionTypes, ...] = (
    "COMUN",
    "ANTICIPADA",
    "BONIFICACION",
    "PENALTY",
    "REDONDEO",
)

DocTypes = Literal["DNI", "CUIL"]
DOC_TYPES: tuple[DocTypes, ...] = ("DNI", "CUIL")

PhoneTypes = Literal["CELULAR", "FIJO", "TRABAJO", "OTRO"]
PHONE_TYPES: tuple[PhoneTypes, ...] = ("CELULAR", "FIJO", "TRABAJO", "OTRO")

RelationshipsTypes = Literal[
    "NO CONSTA", "PERSONAL", "LABORAL", "ESPOSO/A", "PAREJA", "HERMANO/A", "OTRO"
]
RELATIONSHIPS_TYPES: tuple[RelationshipsTypes, ...] = (
    "NO CONSTA",
    "PERSONAL",
    "LABORAL",
    "ESPOSO/A",
    "PAREJA",
    "HERMANO/A",
    "OTRO",
)

MoneyCol = Literal["Capital", "Interest", "IVA", "Total"]

MONEY_COLS: tuple[MoneyCol, ...] = ("Capital", "Interest", "IVA", "Total")
