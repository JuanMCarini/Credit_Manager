# ------------------------------------------------------------
# io/main.py
# ------------------------------------------------------------
# Input/Output utilities for interactive file selection on
# Windows (and other platforms using Tkinter).
#
# This module provides helper functions to:
#   • Open a native file selection dialog
#   • Retrieve user-selected file paths
#   • Integrate file choosing into higher-level workflows
# ------------------------------------------------------------

import tkinter as tk
from tkinter import filedialog  # Windows-native "Open File" and "Save File" dialogs


def select_file():
    """
    ------------------------------------------------------------
    select_file()
    ------------------------------------------------------------
    Open a native Windows file dialog and return the path of the
    selected file, ensuring the dialog appears above all other
    windows.
    ------------------------------------------------------------
    """
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()

    # Force the dialog to appear on top
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    file_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[
            ("All files", "*.*"),
            ("Excel files", "*.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("Text files", "*.txt"),
        ],
        parent=root,  # ensures modality/ownership
    )

    return file_path
