import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/bounces.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            email_to TEXT,
            email_cc TEXT,
            status TEXT,
            reason TEXT,
            domain TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def insert_bounce(email_to, email_cc, status, reason, domain):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bounces (email_to, email_cc, status, reason, domain) VALUES (?, ?, ?, ?, ?)",
        (email_to, email_cc, status, reason, domain),
    )
    conn.commit()
    conn.close()


def query_bounces(start=0, length=25, filters=None):
    """Query bounces with optional filters and pagination"""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM bounces WHERE 1=1"
    params = []

    if filters:
        if "status" in filters and filters["status"]:
            query += " AND status = ?"
            params.append(filters["status"])
        if "domain" in filters and filters["domain"]:
            query += " AND domain = ?"
            params.append(filters["domain"])
        if "date_from" in filters and filters["date_from"]:
            query += " AND date(date) >= date(?)"
            params.append(filters["date_from"])
        if "date_to" in filters and filters["date_to"]:
            query += " AND date(date) <= date(?)"
            params.append(filters["date_to"])

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([length, start])

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_bounces(filters=None):
    """Count bounces with optional filters"""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT COUNT(*) as total FROM bounces WHERE 1=1"
    params = []

    if filters:
        if "status" in filters and filters["status"]:
            query += " AND status = ?"
            params.append(filters["status"])
        if "domain" in filters and filters["domain"]:
            query += " AND domain = ?"
            params.append(filters["domain"])
        if "date_from" in filters and filters["date_from"]:
            query += " AND date(date) >= date(?)"
            params.append(filters["date_from"])
        if "date_to" in filters and filters["date_to"]:
            query += " AND date(date) <= date(?)"
            params.append(filters["date_to"])

    cur.execute(query, tuple(params))
    total = cur.fetchone()[0]
    conn.close()
    return total


# --- Backwards compatibility alias ---
def fetch_bounces(start=0, length=25, filters=None):
    """Alias for query_bounces, kept for compatibility with webui.py"""
    return query_bounces(start, length, filters)