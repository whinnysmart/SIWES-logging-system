import sqlite3

Database = "instance/siwes.db"

def get_db_connection():
    conn = sqlite3.connect(Database)
    conn.row_factory = sqlite3.Row
    return conn
