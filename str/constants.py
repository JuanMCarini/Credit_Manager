from str.database.connection import read_table

df_bp = read_table("business_partners")
OUR_COMPANY_ID = None if df_bp.empty else int(df_bp.index.min())
