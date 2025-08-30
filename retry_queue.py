import sqlite3, os, smtplib, imaplib
from datetime import datetime
from db import DB_PATH
from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv("/data/.env")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT   = int(os.getenv("SMTP_PORT", 587))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER   = os.getenv("IMAP_USER")
IMAP_PASS   = os.getenv("IMAP_PASS")

# Folder mappings
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"
IMAP_FOLDER_INBOX   = os.getenv("IMAP_FOLDER_TEST" if IMAP_TEST_MODE else "IMAP_FOLDER_INBOX", "INBOX")
IMAP_FOLDER_PROBLEM = os.getenv("IMAP_FOLDER_TESTPROBLEM" if IMAP_TEST_MODE else "IMAP_FOLDER_PROBLEM", "PROBLEM")

MAX_RETRIES = 3

def send_notification(bounced_email, subject, reason, cc):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = cc
    msg["Subject"] = f"[Retry] Delivery failed to {bounced_email}"
    msg.set_content(f"Bounce retry: {bounced_email}\nReason: {reason}\nSubject: {subject}")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def move_to_problem(imap_uid):
    conn = imaplib.IMAP4_SSL(IMAP_SERVER)
    conn.login(IMAP_USER, IMAP_PASS)
    conn.select(IMAP_FOLDER_INBOX)
    try:
        conn.copy(imap_uid, IMAP_FOLDER_PROBLEM)
        conn.store(imap_uid, '+FLAGS', '\\Deleted')
        conn.expunge()
    finally:
        conn.logout()

def enqueue_retry(imap_uid, bounced_email, subject, reason, notify_cc):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO retry_queue VALUES(NULL,?,?,?,?,?,?,?)",
              (imap_uid, bounced_email, subject, reason, notify_cc, 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def process_retries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("SELECT * FROM retry_queue WHERE retries < ?", (MAX_RETRIES,)).fetchall()
    for row in rows:
        id, imap_uid, bounced_email, subject, reason, notify_cc, retries, last_attempt = row
        try:
            send_notification(bounced_email, subject, reason, notify_cc)
            c.execute("DELETE FROM retry_queue WHERE id=?", (id,))
        except Exception:
            if retries + 1 >= MAX_RETRIES:
                move_to_problem(imap_uid)
                c.execute("DELETE FROM retry_queue WHERE id=?", (id,))
            else:
                c.execute("UPDATE retry_queue SET retries=retries+1,last_attempt=? WHERE id=?",
                          (datetime.utcnow().isoformat(), id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    process_retries()