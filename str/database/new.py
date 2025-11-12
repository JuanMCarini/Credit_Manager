from typing import Optional

import pandas as pd
from sqlalchemy import text

from str.database.connection import engine
from str.database.get import id as get_id
from str.database.structure import Client
from str.tool import validar_cuit_cuil


def business_partner(name: str, cuil: int | str, email: str) -> int:
    cuil = validar_cuit_cuil(cuil)
    df = pd.DataFrame([{"Company_Name": name, "CUIL": str(cuil), "Email": email}])
    df.to_sql("business_partners", engine, index=False, if_exists="append")
    id = pd.read_sql("business_partners", engine, index_col="ID").index.max()

    return id


def country(name: Optional[str], nationality: Optional[str]) -> int:
    name = str(name).upper().strip()
    nationality = str(nationality).upper().strip()
    df = pd.read_sql("countries", engine, index_col="ID")
    if (name in df["Name"].values) or (nationality in df["Nationality"].values):
        id = df.loc[(df["Name"] == name) | (df["Nationality"] == nationality)].index[0]
    else:
        df = pd.DataFrame([{"Name": name, "Nationality": nationality}])
        df.to_sql("countries", engine, index=False, if_exists="append")
        id = pd.read_sql("countries", engine, index_col="ID").index.max()

    return id


def province(name: Optional[str]) -> int:
    df = pd.read_sql("provinces", engine, index_col="ID")
    name = str(name).upper().strip()
    if name in df["Name"].values:
        id = df.loc[df["Name"] == name].index[0]
    else:
        df = pd.DataFrame([{"Name": name}])
        df.to_sql("provinces", engine, index=False, if_exists="append")
        id = pd.read_sql("provinces", engine, index_col="ID").index.max()

    return id


def city(name: Optional[str], province: Optional[str]) -> int:
    name = str(name).upper().strip()
    df = pd.read_sql("cities", engine, index_col="ID")
    if name in df["Name"].values:
        id = df.loc[df["Name"] == name].index[0]
    else:
        df_provinces = pd.read_sql("provinces", engine, index_col="ID")
        id_province = df_provinces.loc[
            df_provinces["Name"] == str(province).upper()
        ].index[0]
        df = pd.DataFrame([{"Name": name.upper(), "Province_ID": id_province}])
        df.to_sql("cities", engine, index=False, if_exists="append")
        id = pd.read_sql("cities", engine, index_col="ID").index.max()
    return id


def client(
    CUIL: str | int,
    **kw,
) -> Client:
    "Add or update a client"

    CUIL = validar_cuit_cuil(CUIL)

    dni = kw.get("DNI")
    if (dni) and (type(dni) in ["str", "int"]):
        dni = int(dni)
        if dni != int(CUIL) // 10 % 10**8:
            raise ValueError(f"El DNI: {dni} no coincide con el {CUIL}")
    else:
        dni = int(CUIL) // 10 % 10**8

    gender_id = get_id(kw.get("gender"), "genders")
    ms_id = get_id(kw.get("marital_status"), "marital_status")
    id_country = country(kw.get("country"), kw.get("nationality"))
    id_province = province(kw.get("province"))
    id_city = city(kw.get("city"), kw.get("province"))

    payload = {
        "ID": 1,
        "Last_Name": kw.get("last_name"),
        "First_Name": kw.get("first_name"),
        "DNI": dni,
        "CUIL": CUIL,
        "Birth_Date": pd.Period(kw.get("birth"), freq="D"),
        "Gender_ID": gender_id,
        "Marital_Status_ID": ms_id,
        "Nationality_ID": id_country,
        "Province_ID": id_province,
        "City_ID": id_city,
        "Address": kw.get("address"),
        "Email": kw.get("email"),
    }

    df = pd.read_sql("clients", engine, index_col="ID")
    mask = (df["CUIL"] == str(CUIL)) | (df["DNI"] == str(dni))
    exists = not df.loc[mask].empty

    cliente = Client(
        1,
        kw.get("last_name"),
        kw.get("first_name"),
        dni,
        CUIL,
        kw.get("birth"),
        gender_id,
        ms_id,
        id_country,
        id_province,
        id_city,
        kw.get("address"),
        kw.get("email"),
    )

    if exists:
        id = int(df.loc[mask].index[0])
        cols_to_update = {k: v for k, v in payload.items() if v is not None}
        set_fragments = [f"{col} = :{col}" for col in cols_to_update.keys()]
        sql = f"""UPDATE clients SET {", ".join(set_fragments)} WHERE ID = {id}"""
        cols_to_update["status_date"] = str(pd.Period.now("D"))
        cols_to_update["id"] = id
        with engine.begin() as conn:
            conn.execute(text(sql), cols_to_update)
        df = pd.read_sql("clients", engine, index_col="ID")
        cliente = Client(
            id,
            df.at[id, "Last_Name"],
            df.at[id, "First_Name"],
            df.at[id, "DNI"],
            df.at[id, "CUIL"],
            df.at[id, "Birth_Date"],
            df.at[id, "Gender_ID"],
            df.at[id, "Marital_Status_ID"],
            df.at[id, "Nationality_ID"],
            df.at[id, "Province_ID"],
            df.at[id, "City_ID"],
            df.at[id, "Address"],
            df.at[id, "Email"],
        )

    else:
        df = pd.DataFrame([cliente.to_dict()])
        df.set_index("ID", inplace=True)
        df.to_sql("clients", engine, index=False, if_exists="append")
        id = pd.read_sql("clients", engine, index_col="ID").index.max()
        cliente.ID = id

    return cliente


def business_line(name: str, cuit: int | str, abbreviation: str, email: str) -> int:
    name = name.upper().strip()
    if not validar_cuit_cuil(cuit):
        raise ValueError(f"{cuit} no es un CUIT")
    else:
        cuit = str(cuit)
    df = pd.read_sql("business_lines", engine, index_col="ID")
    if cuit in df["CUIT"].values:
        id = df.loc[df["CUIT"] == cuit].index[0]
    else:
        df = pd.DataFrame(
            [{"Name": name, "CUIT": cuit, "abbreviation": abbreviation, "Email": email}]
        )
        df.to_sql("business_lines", engine, index=False, if_exists="append")
        id = pd.read_sql("business_lines", engine, index_col="ID").index.max()

    return id


def organism(name: str, mutual: str, cuit: int | str, email: str) -> int:
    cuit = str(cuit).replace("-", "").replace("/", "")
    if not validar_cuit_cuil(cuit):
        raise ValueError(f"{cuit} no es un CUIT.")
    else:
        cuit = str(cuit)

    name = name.upper().strip()
    df = pd.read_sql("organisms", engine, index_col="ID")
    if (cuit in df["CUIT"].values) | (name in df["Name"].values):
        id = df.loc[(df["CUIT"] == cuit) & (df["Name"] == name)].index[0]
    else:
        df = pd.DataFrame([{"Name": name, "CUIT": cuit, "Email": email}])
        df.to_sql("organisms", engine, index=False, if_exists="append")
        id = pd.read_sql("organisms", engine, index_col="ID").index.max()

    return id
