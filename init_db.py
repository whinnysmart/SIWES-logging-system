import sqlite3

conn = sqlite3.connect('instance/siwes.db')
cursor = conn.cursor()

# Create a table for logs
cursor.execute("DROP TABLE IF EXISTS logs")

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME NOT NULL,
    activity TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    feedback TEXT
)
''')

conn.commit()
conn.close()

print("Database initialized with status and feedback columns.")