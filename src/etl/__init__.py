"""
Module: __init__.py
Description: Package initialization for the ETL (Extract, Transform, Load) module.
             Exposes the PortfolioImporter class for clean and centralized
             API access across the application.
Author: Juan Martín Carini
Date: 2026-05-14
"""

from .csv_importer import PortfolioImporter

# Defines the public interface of the package
__all__ = ["PortfolioImporter"]
