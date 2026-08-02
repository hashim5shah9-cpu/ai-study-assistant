import os
import sys
import json
import sqlite3

# Safe imports for PyMySQL and mysql.connector
pymysql = None
try:
    import pymysql
    import pymysql.cursors
except BaseException:
    pymysql = None

mysql_connector = None
try:
    import mysql.connector
except BaseException:
    mysql_connector = None

pg8000 = None
try:
    import pg8000
except BaseException:
    pg8000 = None


# Persistent JSON Backup path for Vercel Serverless ephemeral /tmp
JSON_BACKUP_PATH = "/tmp/users_persistent_backup.json" if os.path.exists("/tmp") else os.path.join(os.path.dirname(__file__), "users_persistent_backup.json")

def load_json_users_backup():
    if os.path.exists(JSON_BACKUP_PATH):
        try:
            with open(JSON_BACKUP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json_users_backup(raw_conn):
    try:
        cursor = raw_conn.cursor()
        cursor.execute("SELECT user_id, username, email, password_hash, created_at FROM users")
        rows = cursor.fetchall()
        users_list = []
        for r in rows:
            if isinstance(r, sqlite3.Row) or isinstance(r, dict):
                users_list.append({
                    "user_id": r["user_id"],
                    "username": r["username"],
                    "email": r["email"],
                    "password_hash": r["password_hash"],
                    "created_at": str(r["created_at"])
                })
            else:
                users_list.append({
                    "user_id": r[0],
                    "username": r[1],
                    "email": r[2],
                    "password_hash": r[3],
                    "created_at": str(r[4])
                })
        with open(JSON_BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(users_list, f, indent=2)
        cursor.close()
    except Exception as e:
        print(f"Notice: JSON backup save error: {e}")


class SQLiteDictCursor:
    def __init__(self, cursor, conn_wrapper=None):
        self._cursor = cursor
        self._conn_wrapper = conn_wrapper
        self.rowcount = -1

    def execute(self, query, params=()):
        sqlite_query = query.replace("%s", "?")
        sqlite_query = sqlite_query.replace("SELECT DATABASE() as db_name", "SELECT 'sqlite' as db_name")
        self._cursor.execute(sqlite_query, params)
        self.rowcount = self._cursor.rowcount

        # Auto sync JSON backup when users table is updated
        if ("INSERT INTO USERS" in query.upper() or "UPDATE USERS" in query.upper()) and self._conn_wrapper:
            try:
                save_json_users_backup(self._conn_wrapper._raw_conn)
            except Exception:
                pass

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
        self._raw_conn = conn

    def cursor(self, dictionary=True):
        return SQLiteDictCursor(self._conn.cursor(), self)

    def commit(self):
        try:
            self._conn.commit()
            save_json_users_backup(self._raw_conn)
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
        CREATE TABLE IF NOT EXISTS code_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code_input TEXT,
            explanation TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_name TEXT,
            explanation TEXT,
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # If users table is empty, restore from persistent JSON backup
    cursor.execute("SELECT COUNT(*) FROM users")
    count_row = cursor.fetchone()
    user_count = count_row[0] if count_row else 0
    if user_count == 0:
        backup_users = load_json_users_backup()
        for u in backup_users:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (u.get("user_id"), u.get("username"), u.get("email"), u.get("password_hash"), u.get("created_at"))
                )
            except Exception:
                pass
        conn.commit()

    cursor.close()


def get_db_connection():
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "ai_study_assistant")
    db_port = int(os.getenv("DB_PORT", "3306"))
    db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL") or os.getenv("POSTGRES_URL")

    # 1. PyMySQL Connection (For MySQL / MariaDB / phpMyAdmin databases)
    if pymysql:
        try:
            connection = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_pass,
                database=db_name,
                port=db_port,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5
            )
            return connection
        except Exception as e:
            print(f"PyMySQL Connection Notice: {e}. Falling back...")

    # 2. mysql.connector Connection
    if mysql_connector:
        try:
            connection = mysql_connector.connect(
                host=db_host,
                user=db_user,
                password=db_pass,
                database=db_name,
                port=db_port,
                connect_timeout=5
            )
            if connection.is_connected():
                return connection
        except Exception as e:
            print(f"MySQL Connector Connection Notice: {e}. Falling back...")

    # 3. SQLite Fallback (Vercel Serverless / Local Environment with JSON Persistence)
    try:
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