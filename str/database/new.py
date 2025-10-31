import pandas as pd

from str.database.connection import engine

def business_partner(name: str, cuil: int | str, email: str) -> int:
    
    if (len(str(cuil)) != 11):
        raise ValueError(f"{cuil} no es un CUIL")
    else:
        cuil = int(cuil)
    df = pd.DataFrame([{'Company_Name': name, 'CUIL': str(cuil), 'Email': email}])
    df.to_sql('business_partners', engine, index=False, if_exists='append')
    id = pd.read_sql('business_partners', engine, index_col='ID').index.max()
    
    return id

def country(name: str, ) -> int:
    df = pd.DataFrame([{'Name': name.upper()}])
    df.to_sql('countries', engine, index=False, if_exists='append')
    id = pd.read_sql('countries', engine, index_col='ID').index.max()
    return id

def province(name: str) -> int:
    df = pd.DataFrame([{'Name': name.upper()}])
    df.to_sql('provinces', engine, index=False, if_exists='append')
    id = pd.read_sql('province', engine, index_col='ID').index.max()    
    return id

def city(name: str, province: str) -> int:
    df_province = pd.read_sql('provinces', engine, index_col='ID')
    id_province = df_province.loc[df_province['Name'] == province.upper()].index[0]
    df = pd.DataFrame([{'Name': name.upper(), 'Province_ID': id_province}])
    df.to_sql('cities', engine, index=False, if_exists='append')
    id = pd.read_sql('cities', engine, index_col='ID').index.max()
    return id