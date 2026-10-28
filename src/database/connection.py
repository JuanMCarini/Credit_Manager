"""
Module: connection.py
Description: Database engine configuration and session management with isolated local storage.
Author: Juan Martín Carini
Date: 2026-05-08
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import DATABASE_SETTINGS

# Create the engine using the configuration from environment
engine = create_engine(
    DATABASE_SETTINGS.database_url,
    pool_pre_ping=True,
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models to inherit from
Base = declarative_base()


def get_db():
    """
    Utility function to provide a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
