import sqlite3
import os

db_path = 'd:\\Repositorios\\Credit_Manager\\data\\credit_manager.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE procesos ADD COLUMN descripcion TEXT;")
        conn.commit()
        print("Column added successfully.")
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()
else:
    print("Database not found at", db_path)
