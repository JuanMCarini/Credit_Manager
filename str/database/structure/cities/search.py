from str.database.connection import read_table
from str.database.structure.cities.main import City


def search_id(
    city: str | City,
    province: str = "",
    country: str = "",
) -> int:
    """
    ============================================================
      SEARCH CITY ID
    ------------------------------------------------------------
      Dada una ciudad, provincia y país (todas strings), busca
      el ID de la ciudad en la base de datos.

      - Normaliza las entradas (mayúsculas, sin espacios).
      - Hace merge de cities → provinces → countries.
      - Filtra la fila exacta ciudad/provincia/país.
      - Devuelve el ID en caso de coincidencia única.
      - Lanza error si no existe o si hay más de una coincidencia.
    ============================================================
    """

    if isinstance(city, City):
        return city.ID  # type: ignore

    # ---------- Load tables ----------
    cities = read_table("cities")  # tabla de ciudades
    provinces = read_table("provinces")  # tabla de provincias
    countries = read_table("countries")  # tabla de países

    # ---------- Normalize inputs ----------
    city = city.upper().strip()
    province = province.upper().strip()
    country = country.upper().strip()

    # ---------- Join cities → provinces → countries ----------
    merged = cities.merge(
        provinces, left_on="Province_ID", right_index=True, suffixes=("", "_Province")
    ).merge(
        countries, left_on="Country_ID", right_index=True, suffixes=("", "_Country")
    )

    # ---------- Build mask for exact match ----------
    mask = (
        (merged["Name"] == city)
        & (merged["Name_Province"] == province)
        & (merged["Name_Country"] == country)
    )

    matches = merged.loc[mask]

    # ---------- Return or raise ----------
    if len(matches) == 1:
        # Devuelve el índice que es el ID de la ciudad
        return int(matches.index[0])
    elif len(matches) == 0:
        new_city = City(city, province, country)
        city_id = int(new_city.ID)  # type: ignore
        return city_id
    else:
        # Existen duplicados (debería ser imposible si tu sistema está bien)
        raise ValueError(
            f"Ambiguous match: more than one city named {city} in {province}, {country}."
        )
