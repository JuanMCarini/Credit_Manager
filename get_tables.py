import sqlite3
conn = sqlite3.connect('d:/Repositorios/Credit_Manager/data/credit_manager.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(tables)
