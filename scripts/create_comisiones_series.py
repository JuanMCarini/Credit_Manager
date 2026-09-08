"""
Migration script: create comisiones_series table.
Also migrates existing id_comision data from series table if the column still exists.
Run from the project root: python scripts/create_comisiones_series.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = "5434"  # Docker exposed port
DB_NAME = os.getenv("DB_NAME", "postgres")

DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Create comisiones_series table
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS comisiones_series (
                id SERIAL PRIMARY KEY,
                id_serie INTEGER NOT NULL REFERENCES series(id),
                id_comision INTEGER NOT NULL REFERENCES comisiones_deuda(id),
                created_at TIMESTAMP DEFAULT NOW(),
                update_at TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.commit()
        print("Table 'comisiones_series' created (or already existed).")
    except Exception as e:
        conn.rollback()
        print(f"Error creating table: {e}")
        raise

    # 2. Migrate existing id_comision data from series (if the column still exists)
    try:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'series' AND column_name = 'id_comision';
        """))
        col_exists = result.fetchone()

        if col_exists:
            migrated = conn.execute(text("""
                INSERT INTO comisiones_series (id_serie, id_comision)
                SELECT id, id_comision FROM series
                WHERE id_comision IS NOT NULL
                ON CONFLICT DO NOTHING;
            """))
            conn.commit()
            print(f"Migrated existing id_comision rows to comisiones_series.")

            # Drop the old column
            conn.execute(text("ALTER TABLE series DROP COLUMN IF EXISTS id_comision;"))
            conn.commit()
            print("Dropped 'id_comision' column from 'series' table.")
        else:
            print("Column 'id_comision' not found in 'series' — no migration needed.")
    except Exception as e:
        conn.rollback()
        print(f"Error during data migration: {e}")
        raise

    print("Migration completed successfully.")
