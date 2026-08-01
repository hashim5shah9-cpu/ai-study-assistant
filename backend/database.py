import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",          # Agar password rakha hai to likhein, warna khali "" chordein
            password="",          # XAMPP/WAMP me aksar khali "" hota hai
            database="ai_study_assistant" # Exact matching database
        )
        return connection
    except Error as e:
        print(f"MySQL Connection Error: {e}")
        return None