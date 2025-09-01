import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "/data/bounces.db")


def get_connection():
    """Get a connection to the SQLite database with row factory as dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Ensure the database schema exists before use."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bounces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
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
    """Insert a bounce record into the database."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO bounces (date, email_to, email_cc, status, reason, domain)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            email_to,
            email_cc,
            status,
            reason,
            domain,
        ),
    )
    conn.commit()
    conn.close()


def query_bounces(filters=None, limit=25, offset=0, order_by="id ASC"):
    """Fetch bounce records with optional filters, pagination, and ordering."""
    init_db()
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
            query += " AND domain = ?"
            params.append(filters["domain"])

    query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def count_bounces(filters=None):
    """Count total bounce records with optional filters."""
    init_db()
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
            query += " AND domain = ?"
            params.append(filters["domain"])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    total = cur.fetchone()[0]
    conn.close()

    return total