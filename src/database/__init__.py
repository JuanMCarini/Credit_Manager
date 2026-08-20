"""
Module: __init__.py
Description: Initializes the database package, exposing core models and connection utilities.
Author: Juan Martín Carini
Date: 2026-05-08
"""

# Import connection utilities
from .connection import Base, SessionLocal, engine, get_db

# Import seed functions
from .seed_admin import seed_admin
from .seed_geography import seed_provincias
from .seed_conceptos import seed_conceptos
from .seed_bancos import seed_bancos

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
    EstadoClienteEnum,
    SocioComercial,
    TipoCobranzaEnum,
    TipoLiquidacionEnum,
    TipoOperacionCartera,
    EstadoCuota,
    Provincia,
    Empleador,
    TasaYComision,
    EstadoComisionEnum,
    TipoCredito,
    Relacion,
    Transferencia,
    DocumentoLegajo,
    Comercializador,
    Banco,
    Cuenta,
    Concepto,
    Clasificacion,
    Movimiento,
    CategoriaMovimiento,
    Proveedor,
    Comprobante,
    EstadoCheque,
    CalificacionEmisor,
    OperadorCheque,
    Cheque,
    TipoOperacionCheque,
    OperacionCheque,
    PosicionIva,
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
    "EstadoClienteEnum",
    "TipoOperacionCartera",
    "OrigenCredito",
    "EstadoCredito",
    "TipoCobranzaEnum",
    "TipoLiquidacionEnum",
    "EstadoCuota",
    "Provincia",
    "Empleador",
    "TasaYComision",
    "EstadoComisionEnum",
    "TipoCredito",
    "Relacion",
    "seed_admin",
    "seed_provincias",
    "seed_conceptos",
    "seed_bancos",
    "Transferencia",
    "DocumentoLegajo",
    "Comercializador",
    "Banco",
    "Cuenta",
    "Concepto",
    "Clasificacion",
    "Movimiento",
    "CategoriaMovimiento",
    "Proveedor",
    "Comprobante",
    "EstadoCheque",
    "CalificacionEmisor",
    "OperadorCheque",
    "Cheque",
    "TipoOperacionCheque",
    "OperacionCheque",
]
