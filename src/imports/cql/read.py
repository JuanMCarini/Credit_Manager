"""
Module for reading CQL files.

This module is responsible for prompting the user to select a directory
containing the report files exported from CQL system, as well as
the commercial partners configuration file.
It verifies that the required files exist and loads them into pandas DataFrames.
"""

import os
import pandas as pd
from src.utils.files import select_directory
from src.imports.init_socios import ensure_socios_exist

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

# Verify the existence of the mandatory files in the directory
required_files = {
    "Clientes.xlsx": clientes,
    "Reporte - Clientes.xlsx": clientes_reporte,
    "Reporte - Créditos.xlsx": creditos,
    "Reporte - Créditos detalle cuota.xlsx": cuotas,
    "Reporte - Cobranzas.xlsx": cobranzas,
    "Reporte - Inv. Créditos.xlsx": inventario,
    "Socios Comerciales.xlsx": socios,
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

# Initialize commercial partners in the database automatically
ensure_socios_exist(df_socios_excel)