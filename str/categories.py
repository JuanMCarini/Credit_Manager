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

CollectionTypes = Literal["COMUN", "ANTICIPADA", "BONIFICACION", "PENALTY"]
COLLECTION_TYPES: tuple[CollectionTypes, ...] = (
    "COMUN",
    "ANTICIPADA",
    "BONIFICACION",
    "PENALTY",
)

MoneyCol = Literal["Capital", "Interest", "IVA", "Total"]
MONEY_COLS: tuple[MoneyCol, ...] = ("Capital", "Interest", "IVA", "Total")
