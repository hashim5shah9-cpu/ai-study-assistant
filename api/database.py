import os
import sqlite3

# Safe import for mysql.connector
try:
    import mysql.connector
    from mysql.connector import Error
except Exception as e:
    mysql = None
    Error = Exception

class SQLiteDictCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.rowcount = -1

    def execute(self, query, params=()):
        # Convert MySQL %s placeholder to SQLite ? placeholder
        sqlite_query = query.replace("%s", "?")
        sqlite_query = sqlite_query.replace("SELECT DATABASE() as db_name", "SELECT 'sqlite' as db_name")
        self._cursor.execute(sqlite_query, params)
        self.rowcount = self._cursor.rowcount
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, dictionary=True):
        return SQLiteDictCursor(self._conn.cursor())

    def commit(self):
        try:
            self._conn.commit()
        except Exception:
            pass

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

def init_sqlite_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prompt TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS multi_uploaded_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()

def get_db_connection():
    # 1. If DB_HOST is explicitly configured and mysql module available, try MySQL
    db_host = os.getenv("DB_HOST")
    if db_host and mysql and hasattr(mysql, 'connector'):
        try:
            connection = mysql.connector.connect(
                host=db_host,
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "ai_study_assistant"),
                port=int(os.getenv("DB_PORT", "3306")),
                connect_timeout=3
            )
            if connection.is_connected():
                return connection
        except Exception as e:
            print(f"MySQL Connection Notice: {e}. Falling back to SQLite...")

    # 2. SQLite Fallback (Vercel Serverless / Local without MySQL server)
    try:
        # Use /tmp directory on Vercel/Linux serverless environments
        if os.path.exists("/tmp"):
            db_path = "/tmp/ai_study_assistant.db"
        else:
            db_path = os.path.join(os.path.dirname(__file__), "ai_study_assistant.db")
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        init_sqlite_tables(conn)
        return SQLiteConnectionWrapper(conn)
    except Exception as e:
        print(f"SQLite Connection Error: {e}")
        return None