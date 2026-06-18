"""
Module: __init__.py
Description: Initialization file for the utils package. Exposes key utility
             functions for cleaner and more direct imports across the application.
"""

from .dates import normalize_date

# Explicitly define what is exposed by this package
__all__ = ["normalize_date"]
