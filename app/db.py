# db.py
import sqlite3

DB_PATH = "/data/bounces.db"

def init_db():
    """Initialize the SQLite database and create the bounces table if not exists."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            email_to TEXT,
            email_cc TEXT,
            status TEXT,
            reason TEXT,
            domain TEXT,
            retries INTEGER DEFAULT 0
        )
    """)
    con.commit()
    con.close()

def log_bounce(date, email_to, email_cc, status, reason, domain):
    """Insert a new bounce record into the database."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO bounces (date, email_to, email_cc, status, reason, domain) VALUES (?,?,?,?,?,?)",
        (date, email_to, email_cc, status, reason, domain)
    )
    con.commit()
    con.close()

def update_status(bounce_id, status):
    """Update the status of a bounce by its ID."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE bounces SET status=? WHERE id=?", (status, bounce_id))
    con.commit()
    con.close()

def fetch_bounces(limit=25, offset=0, filters=None):
    """
    Fetch a page of bounces with optional filters.
    Supports pagination via LIMIT/OFFSET.
    """
    query = "SELECT * FROM bounces WHERE 1=1"
    params = []

    if filters:
        if filters.get("date_from"):
            query += " AND date >= ?"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            query += " AND date <= ?"
            params.append(filters["date_to"])
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        if filters.get("domain"):
            query += " AND domain LIKE ?"
            params.append(f"%{filters['domain']}%")

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    con.close()
    return [dict(ix) for ix in rows]

def count_bounces(filters=None):
    """
    Count total number of bounces matching optional filters.
    Used for DataTables server-side pagination.
    """
    query = "SELECT COUNT(*) FROM bounces WHERE 1=1"
    params = []

    if filters:
        if filters.get("date_from"):
            query += " AND date >= ?"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            query += " AND date <= ?"
            params.append(filters["date_to"])
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        if filters.get("domain"):
            query += " AND domain LIKE ?"
            params.append(f"%{filters['domain']}%")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(query, tuple(params))
    total = cur.fetchone()[0]
    con.close()
    return total