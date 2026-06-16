"""
Module: config.py
Description: Global configuration module for the portfolio management system.
             Centralizes the master data using pydantic-settings for robust
             type validation and environment variable management.
Author: Juan Martín Carini
Date: 2026-05-13
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CompanyConfig(BaseSettings):
    """
    Data structure representing the company that owns and manages the portfolios.
    Automatically loads and validates values from environment variables or a .env file.
    """

    razon_social: str = Field(
        default="Yoyo S.A.", description="Legal name of the company"
    )
    cuit: str = Field(default="30000000000", description="11-digit Tax ID (CUIT)")
    domicilio: str = Field(default="Bahía Blanca, Buenos Aires, Argentina")
    email_contacto: str = Field(default="admin@yoyo.com.ar")
    telefono: str = Field(default="+54 9 291 000-0000")

    # Configuration for the Pydantic model
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="COMPANY_",  # Maps variables like COMPANY_RAZON_SOCIAL to razon_social
        extra="ignore",
    )

    @field_validator("cuit")
    @classmethod
    def validate_cuit(cls, v: str) -> str:
        """
        Strips non-numeric characters and ensures the CUIT is exactly 11 digits long.
        """
        clean_cuit = "".join(filter(str.isdigit, v))
        if len(clean_cuit) != 11:
            raise ValueError(
                f"The CUIT must contain exactly 11 numerical digits. Value received: {v}"
            )
        return clean_cuit


# Global immutable instance to be imported across the application
# Usage: from config import COMPANY_DATA
COMPANY_DATA = CompanyConfig()

class APIConfig(BaseSettings):
    """
    Configuration for the API server (CORS, security, etc.).
    """
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of allowed origins for CORS."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_", 
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

API_SETTINGS = APIConfig()
