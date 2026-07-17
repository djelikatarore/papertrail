import sqlite3
conn = sqlite3.connect('papertrail.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables trouvées :")
for t in tables:
    print("-", t[0])