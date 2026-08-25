from src.database import SessionLocal
from src.database.models.finance.bancos import Banco

session = SessionLocal()
bancos = session.query(Banco).all()
for b in bancos:
    print(f"Banco: {b.nombre}, ID: {b.id}, Parser Type: {b.parser_type}")
session.close()
