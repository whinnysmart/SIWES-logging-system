import sqlite3

conn = sqlite3.connect('instance/siwes.db')
cursor = conn.cursor()

# Create a table for logs
cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME NOT NULL,
    activity TEXT NOT NULL
)
''')

conn.commit()
conn.close()

print("Database and logs table created successfully.")