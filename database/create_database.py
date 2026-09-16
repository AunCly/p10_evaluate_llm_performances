## Create database based on the schema defined in structure.sql

import os
import sqlite3
from pathlib import Path


def create_database(db_path: str, schema_path: str) -> None:
    """Create a SQLite database at db_path using the schema defined in schema_path."""
    if os.path.exists(db_path):
        print(f"Database already exists at {db_path}.")
        return

    # Read the SQL schema from the file
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Create the database and execute the schema SQL
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"Database created at {db_path} using schema from {schema_path}.")

if __name__ == "__main__":
    # Define paths for the database and schema
    base_path = Path(__file__).parent
    db_path = base_path / "database.sqlite"
    schema_path = base_path / "structure.sql"

    # Create the database
    create_database(db_path, schema_path)