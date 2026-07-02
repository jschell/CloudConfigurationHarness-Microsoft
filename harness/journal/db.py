"""Connection/migration helper for the harness journal (SQLite).

Applies schema.sql idempotently to a journal database file. This is the
only module in the harness that should open a raw connection to the
journal; other code should import `connect()` from here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB_PATH = Path(__file__).parent / "harness.db"


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection to the journal, applying the schema if needed."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply schema.sql against an existing connection. Idempotent."""
    conn.executescript(SCHEMA_PATH.read_text())
    _add_column_if_missing(conn, "hypotheses", "property_conditions", "TEXT")
    _add_column_if_missing(conn, "fixtures", "variants_json", "TEXT")
    _add_column_if_missing(conn, "fixture_history", "variants_json", "TEXT")
    _add_column_if_missing(conn, "fixture_history", "bicep_files_json", "TEXT")
    conn.commit()


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, sql_type: str
) -> None:
    """CREATE TABLE IF NOT EXISTS in schema.sql doesn't add columns to a
    table that already exists -- this covers real databases created
    before a column was added to schema.sql."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    connection = connect(target)
    tables = [
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    print(f"Journal ready at {target}. Tables: {', '.join(tables)}")
    connection.close()
