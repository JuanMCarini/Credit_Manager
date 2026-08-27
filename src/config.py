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
from pathlib import Path

# Absolute path to the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = str(ROOT_DIR / ".env")

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
    dia_corte: int = Field(default=28, description="Día de corte por defecto para la empresa")

    # Configuration for the Pydantic model
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
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
                cbu=socio.cbu or "",
                dia_corte=socio.dia_corte or 28
            )
        return COMPANY_DATA
    finally:
        if db is None:
            session.close()

def update_company_env(socio):
    """
    Sincroniza los datos de un SocioComercial (el principal) hacia el archivo .env
    y la memoria (COMPANY_DATA).
    """
    import os
    
    if Path(ENV_PATH).exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("COMPANY_RAZON_SOCIAL="):
                    f.write(f'COMPANY_RAZON_SOCIAL="{socio.razon_social}"\n')
                elif line.startswith("COMPANY_CUIT="):
                    f.write(f'COMPANY_CUIT={socio.cuit}\n')
                elif line.startswith("COMPANY_DOMICILIO="):
                    f.write(f'COMPANY_DOMICILIO="{socio.domicilio_legal or ""}"\n')
                elif line.startswith("COMPANY_EMAIL_CONTACTO="):
                    f.write(f'COMPANY_EMAIL_CONTACTO="{socio.mail or ""}"\n')
                elif line.startswith("COMPANY_TELEFONO="):
                    f.write(f'COMPANY_TELEFONO="{socio.telefono or ""}"\n')
                elif line.startswith("COMPANY_BANK_ACCOUNT="):
                    f.write(f'COMPANY_BANK_ACCOUNT="{socio.nro_cuenta_bancaria or ""}"\n')
                elif line.startswith("COMPANY_BANK_NAME="):
                    f.write(f'COMPANY_BANK_NAME="{socio.nombre_banco or ""}"\n')
                elif line.startswith("COMPANY_CBU="):
                    f.write(f'COMPANY_CBU="{socio.cbu or ""}"\n')
                elif line.startswith("COMPANY_DIA_CORTE="):
                    f.write(f'COMPANY_DIA_CORTE={socio.dia_corte or 28}\n')
                else:
                    f.write(line)
                    
    COMPANY_DATA.razon_social = socio.razon_social
    COMPANY_DATA.cuit = socio.cuit
    COMPANY_DATA.domicilio = socio.domicilio_legal or ""
    COMPANY_DATA.email_contacto = socio.mail or ""
    COMPANY_DATA.telefono = socio.telefono or ""
    COMPANY_DATA.bank_account = socio.nro_cuenta_bancaria or ""
    COMPANY_DATA.bank_name = socio.nombre_banco or ""
    COMPANY_DATA.cbu = socio.cbu or ""
    COMPANY_DATA.dia_corte = socio.dia_corte or 28

class APIConfig(BaseSettings):
    """
    Configuration for the API server (CORS, security, etc.).
    """
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of allowed origins for CORS."
    )

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
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
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        env_prefix="DB_",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return f"postgresql+pg8000://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

DATABASE_SETTINGS = DatabaseConfig()
