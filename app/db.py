import os
import sqlite3

# Always store DB in /data (persisted via docker-compose bind mount)
DB_PATH = os.getenv("DB_PATH", "/data/bounces.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Ensure the bounces table exists and contains all required columns"""
    conn = get_connection()
    cur = conn.cursor()

    # Base schema
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            email_to TEXT,
            email_cc TEXT,
            status TEXT,
            reason TEXT,
            domain TEXT
        )
    """)

    # Ensure new columns exist (idempotent upgrade)
    cur.execute("PRAGMA table_info(bounces)")
    existing_cols = [row[1] for row in cur.fetchall()]

    if "notified_to" not in existing_cols:
        cur.execute("ALTER TABLE bounces ADD COLUMN notified_to TEXT")
    if "notified_cc" not in existing_cols:
        cur.execute("ALTER TABLE bounces ADD COLUMN notified_cc TEXT")

    conn.commit()
    conn.close()


def insert_bounce(email_to, email_cc, status, reason, domain,
                  notified_to="", notified_cc=""):
    init_db()  # Safety: ensure table exists before inserting
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO bounces 
           (email_to, email_cc, status, reason, domain, notified_to, notified_cc) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (email_to, email_cc, status, reason, domain, notified_to, notified_cc),
    )
    conn.commit()
    conn.close()


def query_bounces(filters=None):
    init_db()  # Safety: ensure table exists before querying
    filters = filters or {}
    query = "SELECT * FROM bounces WHERE 1=1"
    params = []

    if "status" in filters:
        query += " AND status=?"
        params.append(filters["status"])
    if "domain" in filters:
        query += " AND domain=?"
        params.append(filters["domain"])

    if filters.get("group_by") == "domain":
        query = "SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def count_bounces(filters=None):
    init_db()  # Safety: ensure table exists before counting
    filters = filters or {}
    query = "SELECT COUNT(*) FROM bounces WHERE 1=1"
    params = []

    if "status" in filters:
        query += " AND status=?"
        params.append(filters["status"])
    if "domain" in filters:
        query += " AND domain=?"
        params.append(filters["domain"])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    total = cur.fetchone()[0]
    conn.close()
    return total