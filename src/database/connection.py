"""
Module: connection.py
Description: Database engine configuration and session management with isolated local storage.
Author: Juan Martín Carini
Date: 2026-05-08
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Resolve the absolute path to the project root (two levels up from src/database)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Define the data directory at the project root
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Database URL targeting the new isolated directory
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'credit_manager.db')}"

# Create the engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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
