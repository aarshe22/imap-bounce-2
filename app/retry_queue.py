import os
import smtplib
import sqlite3
from email.mime.text import MIMEText
from dotenv import load_dotenv
from db import get_connection

# ============================================
# Load environment
# ============================================
load_dotenv("data/.env")

SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"


# ============================================
# Helpers
# ============================================

def debug(msg: str):
    if DEBUG:
        print(f"[DEBUG] {msg}")


def init_queue():
    """Ensure retry_queue table exists"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retry_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_to TEXT,
            email_cc TEXT,
            subject TEXT,
            body TEXT,
            attempts INTEGER DEFAULT 0,
            last_error TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ============================================
# Main retry logic
# ============================================

def process_retry_queue():
    init_queue()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM retry_queue ORDER BY created ASC")
    rows = cur.fetchall()

    if not rows:
        debug("Retry queue is empty")
        return

    debug(f"Found {len(rows)} messages in retry queue")

    for row in rows:
        msg_id = row["id"]
        to_addr = row["email_to"]
        cc_addr = row["email_cc"]
        subject = row["subject"]
        body = row["body"]
        attempts = row["attempts"]

        debug(f"Retrying message {msg_id} → {to_addr}, attempt {attempts + 1}")

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = SMTP_USER or "noreply@example.com"
            msg["To"] = to_addr
            if cc_addr:
                msg["Cc"] = cc_addr

            recipients = [to_addr] + ([cc_addr] if cc_addr else [])

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                if SMTP_USER and SMTP_PASS:
                    debug("Authenticating to SMTP relay")
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASS)

                server.sendmail(msg["From"], recipients, msg.as_string())

            debug(f"Successfully sent retry message {msg_id} → {to_addr}")

            # Delete after success
            cur.execute("DELETE FROM retry_queue WHERE id=?", (msg_id,))
            conn.commit()

        except Exception as e:
            error_msg = str(e)
            print(f"Error retrying message {msg_id}: {error_msg}")

            # Increment attempts and store error
            cur.execute(
                "UPDATE retry_queue SET attempts=?, last_error=? WHERE id=?",
                (attempts + 1, error_msg, msg_id),
            )
            conn.commit()

    conn.close()
    debug("Retry queue processing complete")


# ============================================
# Entrypoint
# ============================================

if __name__ == "__main__":
    DEBUG = True  # force debug on manual run
    process_retry_queue()