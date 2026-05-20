import tkinter as tk
from pathlib import Path
from tkinter import filedialog


def select_file(title: str = "Select a file") -> Path:
    """
    =============================================================================
    Function: select_file
    Description: Opens a native OS file dialog to select a single file. Forces
                 the window instance to the foreground to guarantee focus above
                 all other active development windows.
    Parameters:
        title (str): The descriptive title to display on the dialog window.
    Returns:
        Path: A pathlib.Path object representing the chosen file destination.
    =============================================================================
    """
    # 1. Crear una ventana raíz oculta para inicializar el diálogo
    root = tk.Tk()
    root.withdraw()

    # 2. Forzar la ventana del diálogo al frente de la pantalla
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    # 3. Lanzar el selector nativo filtrando extensiones comunes de datos
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[
            ("All files", "*.*"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("Text files", "*.txt"),
        ],
        parent=root,
    )

    # 4. Destruir la instancia raíz para liberar memoria de Tkinter
    root.destroy()

    return Path(file_path)


def ask_portfolio_paths() -> dict | None:
    """
    =============================================================================
    Function: ask_portfolio_paths
    Description: Sequentially prompts the user to select the required files for
                 portfolio ingestion (personas, prestamos, cuotas). Validates
                 that all choices are real files before building the paths map.
    Parameters:
        None
    Returns:
        dict | None: Dictionary with explicit keys ('personas', 'prestamos',
                     'cuotas') containing Path objects, or None if any
                     selection was aborted.
    =============================================================================
    """
    print("📂 Iniciando selección secuencial de archivos para la cartera...")

    # 1. Solicitar archivo de clientes/personas
    path_personas = select_file("Seleccionar archivo de PERSONAS (CSV)")
    if not path_personas.is_file():
        print("❌ Operación cancelada: No se seleccionó el archivo de PERSONAS.")
        return None

    # 2. Solicitar archivo de operaciones/préstamos
    path_prestamos = select_file("Seleccionar archivo de PRESTAMOS (CSV)")
    if not path_prestamos.is_file():
        print("❌ Operación cancelada: No se seleccionó el archivo de PRESTAMOS.")
        return None

    # 3. Solicitar archivo de amortizaciones/cuotas
    path_cuotas = select_file("Seleccionar archivo de CUOTAS (CSV)")
    if not path_cuotas.is_file():
        print("❌ Operación cancelada: No se seleccionó el archivo de CUOTAS.")
        return None

    # 4. Consolidar las rutas en la estructura de diccionario requerida
    paths_dict = {
        "personas": path_personas,
        "prestamos": path_prestamos,
        "cuotas": path_cuotas,
    }

    print("📊 Estructura de rutas cargada exitosamente.")
    return paths_dict
