import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Build connection string for psycopg2 through pg8000
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = "5434" # Docker port
DB_NAME = os.getenv("DB_NAME", "postgres")

DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE movimientos_deuda ADD COLUMN id_serie_destino INTEGER REFERENCES series(id);"))
        conn.commit()
        print("Column id_serie_destino added successfully.")
    except Exception as e:
        print("Error:", e)
