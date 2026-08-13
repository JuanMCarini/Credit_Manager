import sqlite3
con = sqlite3.connect('credit_manager.db')
tables = ['bancos', 'cuentas', 'conceptos', 'clasificaciones', 'movimientos']
for t in tables:
    res = con.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'").fetchone()
    if res:
        print(f"--- {t} ---")
        print(res[0])
