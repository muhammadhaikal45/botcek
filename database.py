import sqlite3

conn = sqlite3.connect("users.db")
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    premium INTEGER DEFAULT 0,
    limit_cek INTEGER DEFAULT 20,
    premium_expired TEXT,
    last_reset TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS stats (
    total_check INTEGER
)
''')

conn.commit()

print("Database siap")
