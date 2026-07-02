"""
Module for reading CQL files.

This module is responsible for prompting the user to select a directory
containing the report files exported from CQL system, as well as
the commercial partners configuration file.
It verifies that the required files exist and loads them into pandas DataFrames.
"""

import os
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from src.utils.files import select_directory
from src.imports.init_socios import ensure_socios_exist

@dataclass
class CQLData:
    df_clientes: pd.DataFrame
    df_creditos: pd.DataFrame
    df_cuotas: pd.DataFrame
    df_cobranzas: pd.DataFrame
    df_inventario: pd.DataFrame
    df_socios_excel: pd.DataFrame
    df_transferencias: pd.DataFrame
    legajos_path: Path
    comprobantes_path: Path

def load_cql_data() -> CQLData:
    # Request the folder from the user using a dialog box
    folder_path = select_directory("Select the folder containing CQL files")

    # Validate that a valid directory was selected
    if not folder_path or not folder_path.is_dir():
        raise ValueError("A valid directory must be selected to proceed with the import.")

    # Define the paths of the expected files
    clientes = folder_path / "Clientes.xlsx"
    clientes_reporte = folder_path / "Reporte - Clientes.xlsx"
    creditos = folder_path / "Reporte - Créditos.xlsx"
    cuotas = folder_path / "Reporte - Créditos detalle cuota.xlsx"
    cobranzas = folder_path / "Reporte - Cobranzas.xlsx"
    inventario = folder_path / "Reporte - Inv. Créditos.xlsx"
    socios = folder_path / "Socios Comerciales.xlsx"
    transferencias = folder_path / "Transferencias.TXT"
    legajos = folder_path / "LEGAJOS"
    comprobantes = folder_path / "COMPROBANTES DE TRANSFERENCIAS"

    # Verify the existence of the mandatory files in the directory
    required_files = {
        "Clientes.xlsx": clientes,
        "Reporte - Clientes.xlsx": clientes_reporte,
        "Reporte - Créditos.xlsx": creditos,
        "Reporte - Créditos detalle cuota.xlsx": cuotas,
        "Reporte - Cobranzas.xlsx": cobranzas,
        "Reporte - Inv. Créditos.xlsx": inventario,
        "Socios Comerciales.xlsx": socios,
        "Transferencias.TXT": transferencias,
    }

    # Identify which files are missing
    missing_files = [name for name, path in required_files.items() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "The following required files were not found in the selected folder:\n"
            + "\n".join(f"- {name}" for name in missing_files)
        )

    # Load the files into pandas DataFrames setting the corresponding indices
    df_clientes = pd.read_excel(clientes, index_col="ID")
    df_creditos = pd.read_excel(creditos, index_col="Crédito")
    df_cuotas = pd.read_excel(cuotas)
    df_cobranzas = pd.read_excel(cobranzas)
    df_inventario = pd.read_excel(inventario, index_col="Id. Op.")
    df_socios_excel = pd.read_excel(socios)
    df_transferencias = pd.read_csv(transferencias, sep=';', header=None)
    df_transferencias.columns = ['CBU', 'Fecha', 'monto', 'CUIT', 'credito_id', 'razon_social']
    df_transferencias.drop(columns=["Fecha"], inplace=True)
    df_transferencias["credito_id"] = df_transferencias["credito_id"].map(df_inventario["Clave Externa"])
    
    # Initialize commercial partners in the database automatically
    ensure_socios_exist(df_socios_excel)
    
    return CQLData(
        df_clientes=df_clientes,
        df_creditos=df_creditos,
        df_cuotas=df_cuotas,
        df_cobranzas=df_cobranzas,
        df_inventario=df_inventario,
        df_socios_excel=df_socios_excel,
        df_transferencias=df_transferencias,
        legajos_path=legajos,
        comprobantes_path=comprobantes
    )