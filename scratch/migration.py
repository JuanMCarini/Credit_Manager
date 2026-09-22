import sqlite3
import os
import sys

db_path = os.path.join('d:\\', 'Repositorios', 'Credit_Manager', 'database.db')
print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)

if ('clientes',) in tables:
    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN sujeto_obligado BOOLEAN DEFAULT 0")
        conn.commit()
        print("Column 'sujeto_obligado' added successfully.")
    except Exception as e:
        print("Error adding column:", e)
else:
    print("Table 'clientes' not found!")
conn.close()
