"""
Module: __init__.py
Description: Package initialization for the reporting module.
             Exposes the primary balancing functions for cleaner
             API access across the application.
Author: Juan Martín Carini
Date: 2026-05-14
"""

from .balances import saldos

# Defines the public interface of the package
__all__ = ["saldos"]
