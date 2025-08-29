import sqlite3
from datetime import datetime
DB_PATH = "/data/bounces.db"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS bounces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, message_id TEXT, subject TEXT,
        orig_to TEXT, bounced_email TEXT, reason TEXT, status TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS retry_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imap_uid TEXT, bounced_email TEXT, subject TEXT,
        reason TEXT, notify_cc TEXT, retries INTEGER DEFAULT 0, last_attempt TEXT)""")
    conn.commit(); conn.close()
def log_bounce(msgid, subject, orig_to, bounced_email, reason, status):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO bounces VALUES(NULL,?,?,?,?,?,?,?)",
              (datetime.utcnow().isoformat(), msgid, subject, orig_to, bounced_email, reason, status))
    conn.commit(); conn.close()
