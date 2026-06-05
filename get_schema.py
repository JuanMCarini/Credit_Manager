import sqlite3
conn = sqlite3.connect('d:/Repositorios/Credit_Manager/data/credit_manager.db')
cursor = conn.cursor()
tables = ['provincias', 'empleadores', 'socios_comerciales', 'tasas_y_comisiones', 'relaciones']
res = {}
for t in tables:
    cursor.execute(f'PRAGMA table_info({t})')
    res[t] = [row[1] for row in cursor.fetchall()]
print(res)
