import sqlite3

#Connect to the database
conn = sqlite3.connect('instance/siwes.db')
cursor = conn.cursor()

#Fetch logs
cursor.execute('SELECT * FROM logs')
logs = cursor.fetchall()

#Display logs
for log in logs:
    print(f"ID: {log[0]} | Date: {log[1]} | Activity: {log[2]}")

conn.close()