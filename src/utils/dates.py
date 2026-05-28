"""
Module: dates.py
Description: General utility functions for date parsing and formatting
             across the application.
"""

from datetime import date, datetime

import pandas as pd


def normalize_date(
    input_date: date | datetime | str | pd.Timestamp | None = None,
    as_type: type = datetime,
) -> date | datetime | pd.Timestamp | str:
    """
    =============================================================================
    Function: normalize_date
    Description: Standardizes date inputs across the application. Converts various
                 date formats into a base native date, then casts it to the
                 explicitly requested output type.
    Parameters:
        input_date: The raw date input (string, datetime, Timestamp, or None).
        as_type (type): The desired output type class (e.g., date, datetime,
                        pd.Timestamp, str). Defaults to native date.
    Returns:
        The standardized date cast to the requested type.
    =============================================================================
    """
    # 1. Resolve to a base native date object
    if input_date is None:
        base_date = date.today()
    elif isinstance(input_date, str):
        # The use of pandas allows digesting dashes (2026-03-30) and slashes (2026/03/30) equally
        base_date = pd.to_datetime(input_date).date()
    elif isinstance(input_date, datetime) or isinstance(input_date, pd.Timestamp):
        base_date = input_date.date()
    else:
        base_date = input_date

    # 2. Cast to the explicitly requested output type
    if as_type is date:
        return base_date
    elif as_type is datetime:
        return datetime.combine(base_date, datetime.min.time())
    elif as_type is pd.Timestamp:
        return pd.Timestamp(base_date)
    elif as_type is str:
        return base_date.isoformat()
    else:
        raise TypeError(f"Unsupported output type requested: {as_type}")
