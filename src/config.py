"""
Module: config.py
Description: Global configuration module for the portfolio management system.
             Centralizes the master data using pydantic-settings for robust
             type validation and environment variable management.
Author: Juan Martín Carini
Date: 2026-05-13
"""

from typing import List, Union
from pydantic import Field, field_validator, model_validator
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
    bank_account: str = Field(default="", description="Bank account number")
    bank_name: str = Field(default="", description="Bank name")
    cbu: str = Field(default="", description="CBU")

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

def get_company_data(db=None) -> CompanyConfig:
    from sqlalchemy.orm import Session
    from src.database.connection import SessionLocal
    from src.database.models.socios import SocioComercial

    session = db or SessionLocal()
    try:
        socio = session.query(SocioComercial).filter(SocioComercial.cuit == COMPANY_DATA.cuit).first()
        if socio:
            return CompanyConfig(
                razon_social=socio.razon_social,
                cuit=socio.cuit,
                domicilio=socio.domicilio_legal or "",
                email_contacto=socio.mail or "",
                telefono=socio.telefono or "",
                bank_account=socio.nro_cuenta_bancaria or "",
                bank_name=socio.nombre_banco or "",
                cbu=socio.cbu or ""
            )
        return COMPANY_DATA
    finally:
        if db is None:
            session.close()

class APIConfig(BaseSettings):
    """
    Configuration for the API server (CORS, security, etc.).
    """
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)"
    )
    secure_cookies: bool = Field(
        default=False,
        description="Whether to use secure cookies (HTTPS only)"
    )
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of allowed origins for CORS."
    )
    secret_key: str = Field(
        default="super_secret_key_change_in_production_9s8d7f98s7df987",
        description="JWT Secret Key"
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT Algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=60,
        description="JWT expiration time in minutes"
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

    @model_validator(mode="after")
    def validate_production_settings(self) -> 'APIConfig':
        if self.environment == "production":
            if self.secret_key == "super_secret_key_change_in_production_9s8d7f98s7df987":
                raise ValueError("API_SECRET_KEY must be overridden con a strong secret in production!")
            self.secure_cookies = True
        return self

API_SETTINGS = APIConfig()

class DatabaseConfig(BaseSettings):
    """
    Configuration for the Database connection.
    """
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="postgres", description="Database password")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="credit_manager", description="Database name")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DB_",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return f"postgresql+pg8000://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

DATABASE_SETTINGS = DatabaseConfig()
