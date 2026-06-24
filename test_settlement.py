import traceback
from src.database.connection import SessionLocal
from src.logic.settlements import SettlementManager

sm = SettlementManager(SessionLocal())
try:
    print("Testing with vencimiento dates...")
    sm.obtain_settlement_of_transferred_quota('1', 'Socio ID', '2026-06-24', '1990-01-01', '2026-08-30')
    print("Success")
except Exception as e:
    traceback.print_exc()
