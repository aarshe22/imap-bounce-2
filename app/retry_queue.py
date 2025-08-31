# retry_queue.py
import sqlite3, smtplib, os
from email.message import EmailMessage
from dotenv import load_dotenv
from db import update_status, init_db

load_dotenv()
DB_PATH = "/data/bounces.db"

SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))

NOTIFY_CC = [x.strip() for x in os.getenv("NOTIFY_CC", "").split(",") if x.strip()]
NOTIFY_CC_TEST = [x.strip() for x in os.getenv("NOTIFY_CC_TEST", "").split(",") if x.strip()]
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

init_db()

def retry_bounces():
    """Retry sending notifications for bounces marked as retry_queued."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM bounces WHERE status='retry_queued'")
    rows = cur.fetchall()

    for row in rows:
        try:
            # Decide recipients
            if IMAP_TEST_MODE:
                notify_recipients = NOTIFY_CC_TEST
            else:
                cc_list = row["email_cc"].split(",") if row["email_cc"] else []
                notify_recipients = NOTIFY_CC + cc_list

            if not notify_recipients:
                print(f"No recipients for bounce ID {row['id']} — skipping.")
                update_status(row["id"], "Problem")
                continue

            # Build message
            msg = EmailMessage()
            msg["Subject"] = f"Retry Bounce Notification: {row['email_to']}"
            msg["From"] = "bounce-processor@localhost"
            msg["To"] = ", ".join(notify_recipients)

            cc_display = row["email_cc"] if row["email_cc"] else "None"
            msg.set_content(f"""
Bounce retry notification.

Original To: {row['email_to']}
Original Cc: {cc_display}
Reason: {row['reason']}
""")

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.send_message(msg)

            update_status(row["id"], "Processed")
            print(f"Retried bounce ID {row['id']} -> success")

        except Exception as e:
            print(f"Retry failed for bounce ID {row['id']}: {e}")
            update_status(row["id"], "Problem")

    con.close()

if __name__ == "__main__":
    retry_bounces()