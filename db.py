import psycopg2
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConnection:
    _db_name = ""

    @classmethod
    def set_db_name(cls, db_name: str):
        cls._db_name = db_name

    @classmethod
    def get_connection(cls):
        if not cls._db_name:
            raise ValueError("Database name is not set")

        config = {
            "dbname": cls._db_name,
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        return psycopg2.connect(**config)


def execute_query(query: str, params=None, fetch=True):
    conn = None
    cursor = None
    try:
        conn = DatabaseConnection.get_connection()
        conn.set_session(autocommit=True)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            res = cursor.fetchall()
            return res
        return True
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def check_database_exists(db_name: str) -> bool:
    """Check if a database exists in PostgreSQL."""
    try:
        # Connect to default 'postgres' database to check other databases
        config = {
            "dbname": "postgres",  # Connect to default database
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        conn = psycopg2.connect(**config)
        conn.set_session(autocommit=True)
        cur = conn.cursor()

        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone() is not None

        cur.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"Error checking database existence: {e}")
        return False


def set_db_name(db_name: str) -> str:
    """Set database name after verifying it exists."""
    if not check_database_exists(db_name):
        return f"**Database '{db_name}' does not exist**"
    else:
        DatabaseConnection.set_db_name(db_name)
        return f"**Database '{db_name}' successfully set**"


def check_file_already_processed(file_path: Path | str) -> bool:
    if isinstance(file_path, str):
        file_path = Path(file_path)

    result = execute_query(
        "SELECT COUNT(*) FROM knowledge_snippets WHERE source_file = %s", (file_path.name,)
    )
    return result[0][0] > 0 if result else False


def save_to_db(response: str, source_file: Path | str):
    """Save parsed snippets to PostgreSQL database"""
    if isinstance(source_file, str):
        source_file = Path(source_file)

    snippets = json.loads(response)

    # Create tables if they don't exist
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS knowledge_snippets (
            id SERIAL PRIMARY KEY,
            source_file TEXT,
            theme TEXT,
            snippet TEXT NOT NULL,
            supports TEXT,
            rejects TEXT
        )
    """,
        fetch=False,
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS citations (
            id SERIAL PRIMARY KEY,
            snippet_id INTEGER REFERENCES knowledge_snippets(id) ON DELETE CASCADE,
            citation TEXT NOT NULL
        )
    """,
        fetch=False,
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS aggregated_themes (
            id SERIAL PRIMARY KEY,
            data JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
        fetch=False,
    )

    # For transactions, we need a dedicated connection
    conn = None
    cursor = None
    try:
        conn = DatabaseConnection.get_connection()
        conn.set_session(autocommit=False)
        cursor = conn.cursor()

        valid_snippets = 0
        for snippet in snippets:
            try:
                if not snippet.get("snippet"):
                    print("Skipping invalid snippet - missing required field 'snippet':")
                    print(f"Theme: {snippet.get('theme')}")
                    print(f"Supports: {snippet.get('supports')}")
                    print(f"Rejects: {snippet.get('rejects')}")
                    print("---")
                    continue

                cursor.execute(
                    """
                    INSERT INTO knowledge_snippets (source_file, theme, snippet, supports, rejects)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        source_file.name,
                        snippet.get("theme"),
                        snippet.get("snippet"),
                        snippet.get("supports"),
                        snippet.get("rejects"),
                    ),
                )

                snippet_id = cursor.fetchone()[0]
                valid_snippets += 1

                if "citations" in snippet and snippet["citations"]:
                    for citation in snippet["citations"]:
                        cursor.execute(
                            """
                            INSERT INTO citations (snippet_id, citation)
                            VALUES (%s, %s)
                        """,
                            (snippet_id, citation),
                        )

            except Exception as e:
                print(f"Error inserting snippet or citations: {e}")
                print("Problematic snippet data:")
                print(f"Theme: {snippet.get('theme')}")
                print(f"Snippet: {snippet.get('snippet')}")
                print(f"Supports: {snippet.get('supports')}")
                print(f"Rejects: {snippet.get('rejects')}")
                print("---")
                conn.rollback()
                continue

        conn.commit()
        print(
            f"Successfully inserted {valid_snippets} valid snippets out of {len(snippets)} total from {source_file.name}"
        )

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed")
