import sys
sys.path.append('.')
from src.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT COUNT(*) FROM repet_audit_logs"))
    print(res.scalar())
