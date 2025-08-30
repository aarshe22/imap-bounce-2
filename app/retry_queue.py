# retry_queue.py
import sqlite3, smtplib, os
from db import DB_PATH

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT   = int(os.getenv("SMTP_PORT","587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
NOTIFY_CC   = os.getenv("NOTIFY_CC")

def retry():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM bounces WHERE status='retry_queued' AND retries < 3")
    rows = cur.fetchall()

    for row in rows:
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                msg = f"Subject: Bounce Retry\\n\\nEmail {row['email']} failed with {row['reason']}"
                server.sendmail(SMTP_USER, NOTIFY_CC, msg)
            cur.execute("UPDATE bounces SET status='Processed', retries=retries+1 WHERE id=?", (row["id"],))
        except Exception:
            cur.execute("UPDATE bounces SET retries=retries+1 WHERE id=?", (row["id"],))

    con.commit()
    con.close()

if __name__ == "__main__":
    retry()