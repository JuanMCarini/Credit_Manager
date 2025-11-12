import pandas as pd

from str.database.connection import engine


def country_nationality(name: str = "", nationality: str = "") -> int:
    df_nationality = pd.read_sql("countries", engine, index_col="ID")
    name = name.upper()
    nationality = nationality.upper()
    filtro = (df_nationality["Name"] == name) | (
        df_nationality["Nationality"] == nationality
    )
    if df_nationality.loc[filtro].empty:
        raise ValueError(
            f'No esta el país/nacionalidad "{name}"/"{nationality}" en la tabla de países.'
        )
    else:
        id = df_nationality.loc[filtro].index[0]

    return id


def province(name: str = "") -> int:
    df_nationality = pd.read_sql("province", engine, index_col="ID")
    name = name.upper()
    filtro = df_nationality["Name"] == name
    if df_nationality.loc[filtro].empty:
        raise ValueError(f'No esta el provincia "{name}" en la tabla de provincias.')
    else:
        id = df_nationality.loc[filtro].index[0]

    return id


def city(name: str = "") -> int:
    df_nationality = pd.read_sql("cities", engine, index_col="ID")
    name = name.upper()
    filtro = df_nationality["Name"] == name
    if df_nationality.loc[filtro].empty:
        raise ValueError(f'No esta la ciudad "{name}" en la tabla de ciudades.')
    else:
        id = df_nationality.loc[filtro].index[0]

    return id
