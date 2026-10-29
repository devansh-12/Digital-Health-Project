"""Manage the SQLite connection and schema migrations."""

import re
import sqlite3
from pathlib import Path

_MIGRATION_NAME = re.compile(r"^(?P<version>\d{3,})_[a-z0-9_]+\.sql$")
_DEFAULT_MIGRATIONS_DIR = Path(__file__).with_name("migrations")


class MigrationError(RuntimeError):
    """Raised when a database migration cannot be applied safely."""


def open_database(path: str | Path) -> sqlite3.Connection:
    """Open a local SQLite database, enable WAL, and apply pending migrations."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        run_migrations(connection)
    except Exception:
        connection.close()
        raise
    return connection


def run_migrations(
    connection: sqlite3.Connection,
    migrations_dir: str | Path = _DEFAULT_MIGRATIONS_DIR,
) -> None:
    """Apply each unapplied numbered SQL migration in its own transaction."""
    migration_path = Path(migrations_dir)
    migrations = _discover_migrations(migration_path)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
        """
    )
    connection.commit()

    applied_versions = {
        int(row[0])
        for row in connection.execute("SELECT version FROM schema_migrations")
    }

    for version, migration_file in migrations:
        if version in applied_versions:
            continue

        migration_sql = migration_file.read_text(encoding="utf-8")
        try:
            connection.execute("BEGIN IMMEDIATE")
            _execute_migration(connection, migration_sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (version, migration_file.name),
            )
            connection.commit()
        except Exception as error:
            connection.rollback()
            raise MigrationError(
                f"Failed to apply migration {migration_file.name}"
            ) from error


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    if not migrations_dir.is_dir():
        raise MigrationError(f"Migration directory does not exist: {migrations_dir}")

    migrations: list[tuple[int, Path]] = []
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        match = _MIGRATION_NAME.fullmatch(migration_file.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {migration_file.name}")
        migrations.append((int(match.group("version")), migration_file))

    versions = [version for version, _ in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Migration version numbers must be unique")
    return migrations


def _execute_migration(connection: sqlite3.Connection, migration_sql: str) -> None:
    statement = ""
    for line in migration_sql.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            if statement.strip():
                connection.execute(statement)
            statement = ""

    if statement.strip():
        raise MigrationError("Migration contains an incomplete SQL statement")
