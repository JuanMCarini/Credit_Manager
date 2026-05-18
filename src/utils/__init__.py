"""
Module: __init__.py
Description: Initialization file for the utils package. Exposes key utility
             functions for cleaner and more direct imports across the application.
"""

from .dates import normalize_date

# Definimos explícitamente qué expone este paquete
__all__ = ["normalize_date"]
