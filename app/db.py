# db.py
"""
Database layer for IMAP Bounce App.

Provides SQLite3 persistence for:
  - Bounces log (email, cc, status, reason, domain, date)
  - Bounce patterns (regex → reason)
  
Tables are created automatically on import.
"""

import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/bounces.db")


def get_connection():
    """Open a SQLite connection with row_factory as dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Ensure required tables exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Bounces log
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

    # Bounce patterns
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL,
            reason TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def insert_bounce(date, email_to, email_cc, status, reason, domain):
    """Insert a new bounce row."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bounces (date, email_to, email_cc, status, reason, domain) VALUES (?, ?, ?, ?, ?, ?)",
        (date, email_to, email_cc, status, reason, domain),
    )
    conn.commit()
    conn.close()


def query_bounces(filters=None, limit=25, offset=0, order_by="id ASC"):
    """Fetch bounces with optional filters (for DataTables)."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM bounces WHERE 1=1"
    params = []

    if filters:
        if "date_from" in filters and filters["date_from"]:
            query += " AND date >= ?"
            params.append(filters["date_from"])
        if "date_to" in filters and filters["date_to"]:
            query += " AND date <= ?"
            params.append(filters["date_to"])
        if "status" in filters and filters["status"]:
            query += " AND status = ?"
            params.append(filters["status"])
        if "domain" in filters and filters["domain"]:
            query += " AND domain = ?"
            params.append(filters["domain"])

    query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_bounces(filters=None):
    """Count bounces for pagination."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT COUNT(*) as count FROM bounces WHERE 1=1"
    params = []

    if filters:
        if "date_from" in filters and filters["date_from"]:
            query += " AND date >= ?"
            params.append(filters["date_from"])
        if "date_to" in filters and filters["date_to"]:
            query += " AND date <= ?"
            params.append(filters["date_to"])
        if "status" in filters and filters["status"]:
            query += " AND status = ?"
            params.append(filters["status"])
        if "domain" in filters and filters["domain"]:
            query += " AND domain = ?"
            params.append(filters["domain"])

    cur.execute(query, tuple(params))
    count = cur.fetchone()["count"]
    conn.close()
    return count


def insert_pattern(pattern, reason):
    """Insert a new bounce regex pattern."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO patterns (pattern, reason) VALUES (?, ?)", (pattern, reason))
    conn.commit()
    conn.close()


def get_patterns():
    """Return all bounce patterns."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patterns")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Ensure DB schema exists at module import
create_tables()