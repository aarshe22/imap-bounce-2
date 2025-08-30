# db.py
import sqlite3

DB_PATH = "/data/bounces.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            email TEXT,
            status TEXT,
            reason TEXT,
            domain TEXT,
            retries INTEGER DEFAULT 0
        )
    """)
    con.commit()
    con.close()

def log_bounce(date, email, status, reason, domain):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO bounces (date, email, status, reason, domain) VALUES (?,?,?,?,?)",
        (date, email, status, reason, domain)
    )
    con.commit()
    con.close()

def update_status(bounce_id, status):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE bounces SET status=? WHERE id=?", (status, bounce_id))
    con.commit()
    con.close()

def fetch_bounces(limit=100):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM bounces ORDER BY date DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return [dict(ix) for ix in rows]