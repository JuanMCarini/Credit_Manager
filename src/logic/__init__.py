"""
Module: __init__.py
Description: Initializes the logic package, exposing financial engines.
Author: Juan Martín Carini
Date: 2026-05-11
"""

from .amortization import AmortizationEngine
from .origination import LoanOriginator

__all__ = ["AmortizationEngine", "LoanOriginator"]
