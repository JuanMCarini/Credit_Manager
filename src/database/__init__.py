"""
Module: __init__.py
Description: Initializes the database package, exposing core models and connection utilities.
Author: Juan Martín Carini
Date: 2026-05-08
"""

# Import connection utilities
from .connection import Base, SessionLocal, engine, get_db

# Import all ORM models to ensure they are registered with SQLAlchemy's Base metadata
from .models import (
    Cartera,
    Cliente,
    Cobranza,
    Credito,
    Cuota,
    EstadoCredito,
    LiquidacionCuotaCedida,
    OperacionCartera,
    OrigenCredito,
    SexoEnum,
    SocioComercial,
    TipoCobranzaEnum,
    TipoLiquidacionEnum,
    TipoOperacionCartera,
    EstadoCuota,
)

# Import events to register SQLAlchemy event listeners
from . import events

# Explicitly define what is available when importing * from the database package
__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "Cliente",
    "SocioComercial",
    "Cartera",
    "Credito",
    "Cuota",
    "OperacionCartera",
    "Cobranza",
    "LiquidacionCuotaCedida",
    "SexoEnum",
    "TipoOperacionCartera",
    "OrigenCredito",
    "EstadoCredito",
    "TipoCobranzaEnum",
    "TipoLiquidacionEnum",
    "EstadoCuota",
]
