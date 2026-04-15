"""
One-time migration script: SQLite (data.db) -> Supabase (PostgreSQL)

Usage:
    python migrate_to_supabase.py
"""

import os
import sqlite3
from sqlalchemy import create_engine, text

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, 'data.db')

# Target: Supabase PostgreSQL (reads from DATABASE_URL env var)
PG_URL = os.environ.get('DATABASE_URL')
if not PG_URL:
    raise RuntimeError('DATABASE_URL environment variable is not set. '
                       'Copy .env.example to .env and fill in your credentials.')

# Tables in dependency order (parents before children)
TABLES = ['users', 'accounts', 'wx_sessions', 'subscriptions', 'articles', 'read_history']


def migrate():
    if not os.path.exists(SQLITE_PATH):
        print(f'SQLite database not found at {SQLITE_PATH}')
        return

    # Connect to source (SQLite)
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to target (PostgreSQL)
    pg_engine = create_engine(PG_URL)

    with pg_engine.connect() as pg_conn:
        for table in TABLES:
            rows = sqlite_conn.execute(f'SELECT * FROM {table}').fetchall()
            if not rows:
                print(f'  {table}: 0 rows (skipped)')
                continue

            columns = rows[0].keys()
            col_list = ', '.join(columns)
            param_list = ', '.join(f':{c}' for c in columns)

            # Clear existing data in target table
            pg_conn.execute(text(f'DELETE FROM {table}'))

            # Insert rows (convert SQLite integer booleans to Python bool for PG)
            bool_columns = {'is_active'}
            insert_sql = text(f'INSERT INTO {table} ({col_list}) VALUES ({param_list})')
            for row in rows:
                row_dict = dict(row)
                for col in bool_columns:
                    if col in row_dict:
                        row_dict[col] = bool(row_dict[col])
                pg_conn.execute(insert_sql, row_dict)

            print(f'  {table}: {len(rows)} rows migrated')

            # Reset the sequence for tables with an 'id' column
            if 'id' in columns:
                pg_conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 0) FROM {table}))"
                ))

        pg_conn.commit()

    sqlite_conn.close()
    print('\nMigration completed successfully!')


if __name__ == '__main__':
    migrate()
