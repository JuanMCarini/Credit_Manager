# ------------------------------------------------------------
# io/__init__.py
# ------------------------------------------------------------
# Public interface for the IO utilities module.
#
# This package exposes high-level helpers for interacting with
# the operating system’s file selection dialogs (Windows/Mac/Linux)
# through Tkinter. Additional IO-related tools can be added here
# and exported via __all__ as the module grows.
# ------------------------------------------------------------

from str.io.main import select_file

# Explicitly define the public API of this package
__all__ = ["select_file"]
