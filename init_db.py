from flask_bcrypt import Bcrypt
import sqlite3
import os

DB_PATH = "instance/siwes.db"

# Remove the old DB (optional for a fresh start)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Removed existing database at {DB_PATH}")

# Create connection
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create Users table
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'supervisor', 'admin')),
        supervisor_id INTEGER,
        FOREIGN KEY (supervisor_id) REFERENCES users(id)
    )
''')

# Create Logs table
cursor.execute('''
    CREATE TABLE logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date DATETIME NOT NULL,
        activity TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        feedback TEXT,
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
''')

# Create default admin user
bcrypt = Bcrypt()
pw_hash = bcrypt.generate_password_hash("adminpass").decode('utf-8')

cursor.execute('''
    INSERT INTO users (username, password_hash, role)
    VALUES (?, ?, ?)
''', ('admin', pw_hash, 'admin'))

# Save and close
conn.commit()
conn.close()

print("Database initialized successfully with users, logs, and default admin.")