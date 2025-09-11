from flask_bcrypt import Bcrypt
import sqlite3
import os

DB_PATH = "instance/siwes.db"

# if os.path.exists(DB_PATH):
#     os.remove(DB_PATH)
#     print(f"Removed existing database at {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# #Create a table for users
# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         username TEXT NOT NULL UNIQUE,
#         password_hash TEXT NOT NULL,
#         role TEXT NOT NULL CHECK(role IN ('student', 'supervisor', 'admin')),
#         supervisor_id INTEGER REFERENCES users(id)
#     )
# ''')

# #Create a table for logs
# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS logs (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id INTEGER NOT NULL,
#         date DATETIME NOT NULL,
#         activity TEXT NOT NULL,
#         status TEXT DEFAULT 'pending',
#         feedback TEXT
#     )
# ''')

# conn.commit()
# conn.close()

# print("Database initialized with user_id in logs table!.")

# cursor.execute("ALTER TABLE logs ADD COLUMN student_id INTEGER;")

# conn.commit()
# conn.close()

# print("student_id column added successfully!")

# Assign student ID to supervisor
# cursor.execute("UPDATE users SET supervisor_id = ? WHERE id = ?", (2, 1))
# cursor.execute("UPDATE users SET supervisor_id = ? WHERE id = ?", (4, 3))

# conn.commit()
# conn.close()

bcrypt = Bcrypt()
pw_hash = bcrypt.generate_password_hash("adminpass").decode('utf-8')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert admin user
cursor.execute('''
    INSERT INTO users (username, password_hash, role) 
    VALUES (?, ?, ?)
''', ('admin', pw_hash, 'admin'))

conn.commit()
conn.close()

print("Admin user created successfully with username 'admin' and password 'adminpass'.")