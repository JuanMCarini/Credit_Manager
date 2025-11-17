from str.database.connection import read_table

# ---------- Load tables ----------
df_countries = read_table("countries", "Name")  # tabla de países
df_provinces = read_table("provinces", "Name")  # tabla de provincias
df_cities = read_table("cities", "Name")  # tabla de ciudades

geo_types = """#geo_types.py
from typing import Literal

Country = Literal[
"""

init_prim = """# categories/__init__.py
from str.categories.main import Genders, MaritalStatus, DocTypes, PhoneTypes, RelationshipsTypes, CreditTypes
from str.categories.geo_types import Country, Province, City"""
init_sec = """__all__ = ['Genders', 'MaritalStatus', 'DocTypes', 'PhoneTypes', 'RelationshipsTypes', 'CreditTypes', 'Country', 'Province', 'City'"""
for country in df_countries.index.values:
    geo_types += f"    '{country}',\n"
geo_types += "    ]\n\n"
for country in df_countries.index.values:
    mask = df_provinces["Country_ID"] == df_countries.at[country, "ID"]
    country_provinces = df_provinces.loc[mask]
    if not country_provinces.empty:
        name = f"Provinces{str(country).title().replace(' ', '')}"
        geo_types += f"{name} = Literal[\n"
        init_prim += f", {name}"
        init_sec += f", '{name}'"
        for province in country_provinces.index.values:
            geo_types += f"    '{province}',\n"
        geo_types += "    ]\n"
geo_types += "\n"
for country in df_countries.index.values:
    mask = df_provinces["Country_ID"] == df_countries.at[country, "ID"]
    country_provinces = df_provinces.loc[mask]
    if not country_provinces.empty:
        for province in country_provinces.index.values:
            mask = df_cities["Province_ID"] == df_provinces.at[province, "ID"]
            province_cities = df_cities.loc[mask]
            name = f"Cities{str(country).title().replace(' ', '')}{str(province).title().replace(' ', '')}"
            geo_types += f"{name} = Literal[\n"
            init_prim += f", {name}"
            init_sec += f", '{name}'"
            for city in province_cities.index.values:
                geo_types += f"    '{city}',\n"
            geo_types += "    ]\n"

geo_types += "\n"
geo_types += """Province = Literal["""
for province in df_provinces.index.values:
    geo_types += f"'{province}',\n"
geo_types += "    ]\n\n"

geo_types += """City = Literal["""
for city in df_cities.index.values:
    geo_types += f"'{city}',\n"
geo_types += "    ]\n\n"

init_prim += "\n\n"
init_sec += "]"

with open("str/categories/geo_types.py", "w", encoding="utf-8") as f:
    f.write(geo_types)

init = init_prim + init_sec
with open("str/categories/__init__.py", "w", encoding="utf-8") as f:
    f.write(init)
