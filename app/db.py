# db.py
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "/data/bounces.db")


def get_connection():
    """Return a SQLite connection with row access by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema if not already created."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            email_to TEXT,
            email_cc TEXT,
            status TEXT,
            reason TEXT,
            domain TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_bounce(date, email_to, email_cc, status, reason, domain):
    """Insert a bounce log entry into the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bounces (date, email_to, email_cc, status, reason, domain)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date, email_to, email_cc, status, reason, domain))
    conn.commit()
    conn.close()


def fetch_bounces(filters=None, start=0, length=25):
    """
    Fetch bounce records with optional filters and pagination.
    Filters: dict with keys 'date_from', 'date_to', 'status', 'domain'
    """
    filters = filters or {}
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM bounces WHERE 1=1"
    params = []

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
        query += " AND domain = ?"
        params.append(filters["domain"])

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([length, start])

    cur.execute(query, tuple(params))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def count_bounces(filters=None):
    """Count bounce records with optional filters (used for DataTables)."""
    filters = filters or {}
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT COUNT(*) FROM bounces WHERE 1=1"
    params = []

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
        query += " AND domain = ?"
        params.append(filters["domain"])

    cur.execute(query, tuple(params))
    total = cur.fetchone()[0]
    conn.close()
    return total


def top_domains(limit=5):
    """Return top domains by bounce volume."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT domain, COUNT(*) as count
        FROM bounces
        GROUP BY domain
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows