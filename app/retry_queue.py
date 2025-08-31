# retry_queue.py
import sqlite3, smtplib, os
from db import DB_PATH

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT   = int(os.getenv("SMTP_PORT","587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")

NOTIFY_CC      = os.getenv("NOTIFY_CC", "")
NOTIFY_CC_TEST = os.getenv("NOTIFY_CC_TEST", "")
TEST_MODE      = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

def get_notification_recipients(cc_str: str) -> list[str]:
    """Build recipient list for notifications."""
    if TEST_MODE:
        return [addr.strip() for addr in NOTIFY_CC_TEST.split(",") if addr.strip()]
    else:
        env_cc = [addr.strip() for addr in NOTIFY_CC.split(",") if addr.strip()]
        cc_list = [addr.strip() for addr in cc_str.split(",") if addr.strip()]
        return list(set(env_cc + cc_list))  # dedupe

def retry():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM bounces WHERE status='retry_queued' AND retries < 3")
    rows = cur.fetchall()

    for row in rows:
        recipients = get_notification_recipients(row["email_cc"])
        if not recipients:
            continue
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                msg = f"Subject: Bounce Notification\n\n" \
                      f"Original To: {row['email_to']}\n" \
                      f"CC: {row['email_cc']}\n" \
                      f"Reason: {row['reason']}\n"
                server.sendmail(SMTP_USER, recipients, msg)
            cur.execute("UPDATE bounces SET status='Processed', retries=retries+1 WHERE id=?", (row["id"],))
        except Exception:
            cur.execute("UPDATE bounces SET retries=retries+1 WHERE id=?", (row["id"],))

    con.commit()
    con.close()

if __name__ == "__main__":
    retry()