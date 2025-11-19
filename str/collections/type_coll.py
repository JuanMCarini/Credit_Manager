# collection/type_coll.py

from str.database import read_table

# Load collection types (indexed by "Type" for lookup)
df_coll_type = read_table("collection_types", "Type")
common_id: int = df_coll_type.at["COMUN", "ID"]  # type: ignore
penalty_id: int = df_coll_type.at["PENALTY", "ID"]  # type: ignore
round_id: int = df_coll_type.at["REDONDEO", "ID"]  # type: ignore
advance_id: int = df_coll_type.at["ANTICIPADA", "ID"]  # type: ignore
bonus_id: int = df_coll_type.at["BONIFICACION", "ID"]  # type: ignore
