"""
Module: connection.py
Description: Database engine configuration and session management with isolated local storage.
Author: Juan Martín Carini
Date: 2026-05-08
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_SETTINGS

# Create the engine using the configuration from environment
engine = create_engine(
    DATABASE_SETTINGS.database_url,
    # You might want to add pool_size or max_overflow here for production
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



