"""
Module: __init__.py
Description: Initializes the logic package, exposing financial engines and managers
             for clean API access.
Author: Juan Martín Carini
Date: 2026-05-11
"""

from .amortization import AmortizationEngine
from .collections import CollectionManager, IdentificadorEnum
from .origination import LoanOriginator
from .penalties import PenaltyManager

__all__ = [
    "AmortizationEngine",
    "CollectionManager",
    "IdentificadorEnum",
    "LoanOriginator",
    "PenaltyManager",
]
