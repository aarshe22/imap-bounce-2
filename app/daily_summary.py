# daily_summary.py
import os, sqlite3, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
DB_PATH = "/data/bounces.db"

SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))

NOTIFY_CC = [x.strip() for x in os.getenv("NOTIFY_CC", "").split(",") if x.strip()]
NOTIFY_CC_TEST = [x.strip() for x in os.getenv("NOTIFY_CC_TEST", "").split(",") if x.strip()]
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

def send_summary():
    """Send daily summary of bounces in the last 24 hours."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    since = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    # Total summary
    cur.execute("SELECT status, COUNT(*) as count FROM bounces WHERE date >= ? GROUP BY status", (since,))
    status_counts = cur.fetchall()

    # Domain summary
    cur.execute("SELECT domain, COUNT(*) as count FROM bounces WHERE date >= ? GROUP BY domain ORDER BY count DESC", (since,))
    domain_counts = cur.fetchall()

    con.close()

    # Decide recipients
    if IMAP_TEST_MODE:
        notify_recipients = NOTIFY_CC_TEST
    else:
        notify_recipients = NOTIFY_CC

    if not notify_recipients:
        print("No recipients defined for daily summary.")
        return

    # Build summary text
    body = f"📬 Daily Bounce Summary (since {since} UTC)\n\n"

    if status_counts:
        body += "By Status:\n"
        for row in status_counts:
            body += f" - {row['status']}: {row['count']}\n"
        body += "\n"

    if domain_counts:
        body += "By Domain:\n"
        for row in domain_counts:
            body += f" - {row['domain']}: {row['count']}\n"
        body += "\n"

    if not status_counts and not domain_counts:
        body += "No bounces recorded in the last 24 hours.\n"

    # Send email
    msg = EmailMessage()
    msg["Subject"] = "Daily Bounce Summary"
    msg["From"] = "bounce-processor@localhost"
    msg["To"] = ", ".join(notify_recipients)
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.send_message(msg)

    print(f"Daily summary sent to: {', '.join(notify_recipients)}")

if __name__ == "__main__":
    send_summary()