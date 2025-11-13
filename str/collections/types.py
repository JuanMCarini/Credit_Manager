# collections/types.py
from __future__ import annotations

from typing import Literal

from str.database.structure import (
    OUR_COMPANY_ID,
    CollectionType,
    Credit,
    CreditType,
    Identifier,
)

__all__ = [
    "OUR_COMPANY_ID",
    "CollectionType",
    "Credit",
    "CreditType",
    "Identifier",
]


MoneyCol = Literal["Capital", "Interest", "IVA", "Total"]
MONEY_COLS: tuple[MoneyCol, ...] = ("Capital", "Interest", "IVA", "Total")
