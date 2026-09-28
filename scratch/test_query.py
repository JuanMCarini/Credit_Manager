import sys
import pandas as pd
sys.path.append('.')
from src.database import SessionLocal
from src.database.models import Cliente, RepetAuditLog

db = SessionLocal()
query = (db.query(RepetAuditLog)
         .join(Cliente))
try:
    df_repet = pd.read_sql(query.statement, db.get_bind())
    print("Query successful. Shape:", df_repet.shape)
except Exception as e:
    print("Error:", e)
finally:
    db.close()
