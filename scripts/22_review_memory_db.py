import sqlite3
import json

DB = "data/memory/lessons.sqlite"

conn = sqlite3.connect(DB)

cursor = conn.cursor()

print("\n=== Tables ===")
cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
""")

for row in cursor.fetchall():
    print(row[0])

print("\n=== Schema ===")
cursor.execute("""
PRAGMA table_info(lessons)
""")

for row in cursor.fetchall():
    print(row)

print("\n=== Sample Rows ===")

cursor.execute("""
SELECT *
FROM lessons
LIMIT 5
""")

for row in cursor.fetchall():
    print()
    print(json.dumps(row, indent=2, default=str))

conn.close()