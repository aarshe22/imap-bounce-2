import sqlite3
import os

DB_PATH = os.path.join(os.getenv("DATA_DIR", "/data"), "bounces.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
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
    conn.commit()
    conn.close()


def log_bounce(email_to, email_cc, status, reason):
    domain = ""
    if email_to and "@" in email_to:
        domain = email_to.split("@")[-1]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bounces (email_to, email_cc, status, reason, domain)
        VALUES (?, ?, ?, ?, ?)
    """, (
        email_to,
        ", ".join(email_cc) if isinstance(email_cc, list) else str(email_cc),
        status,
        reason,
        domain
    ))
    conn.commit()
    conn.close()


def query_bounces(offset=0, limit=25, filters=None):
    filters = filters or {}
    query = "SELECT id, date, email_to, email_cc, status, reason, domain FROM bounces WHERE 1=1"
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
    params.extend([limit, offset])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "date": r[1],
            "email_to": r[2],
            "email_cc": r[3],
            "status": r[4],
            "reason": r[5],
            "domain": r[6],
        }
        for r in rows
    ]


def count_bounces(filters=None):
    filters = filters or {}
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

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    count = cur.fetchone()[0]
    conn.close()
    return count


# Ensure schema always exists at startup
create_tables()