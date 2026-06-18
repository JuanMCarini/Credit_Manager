from pathlib import Path

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
    import tkinter as tk
    from tkinter import filedialog
    # 1. Create a hidden root window to initialize the dialog
    root = tk.Tk()
    root.withdraw()

    # 2. Force the dialog window to the front of the screen
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    # 3. Launch the native selector filtering common data extensions
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

    # 4. Destroy the root instance to free Tkinter memory
    root.destroy()

    return Path(file_path)


def select_directory(title: str = "Select a folder") -> Path:
    """
    =============================================================================
    Function: select_directory
    Description: Opens a native OS directory dialog to select a folder. Forces
                 the window instance to the foreground to guarantee focus above
                 all other active development windows.
    Parameters:
        title (str): The descriptive title to display on the dialog window.
    Returns:
        Path: A pathlib.Path object representing the chosen directory.
    =============================================================================
    """
    import tkinter as tk
    from tkinter import filedialog
    # 1. Create a hidden root window to initialize the dialog
    root = tk.Tk()
    root.withdraw()

    # 2. Force the dialog window to the front of the screen
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    # 3. Launch the native directory selector
    dir_path = filedialog.askdirectory(
        title=title,
        parent=root,
    )

    # 4. Destroy the root instance to free Tkinter memory
    root.destroy()

    return Path(dir_path)


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
    print("📂 Starting sequential file selection for the portfolio...")

    # 1. Request clients/persons file
    path_personas = select_file("Select PERSONAS file (CSV)")
    if not path_personas.is_file():
        print("❌ Operation cancelled: PERSONAS file was not selected.")
        return None

    # 2. Request operations/loans file
    path_prestamos = select_file("Select PRESTAMOS file (CSV)")
    if not path_prestamos.is_file():
        print("❌ Operation cancelled: PRESTAMOS file was not selected.")
        return None

    # 3. Request installments file
    path_cuotas = select_file("Select CUOTAS file (CSV)")
    if not path_cuotas.is_file():
        print("❌ Operation cancelled: CUOTAS file was not selected.")
        return None

    # 4. Consolidate paths into the required dictionary structure
    paths_dict = {
        "personas": path_personas,
        "prestamos": path_prestamos,
        "cuotas": path_cuotas,
    }

    print("📊 Paths structure loaded successfully.")
    return paths_dict
