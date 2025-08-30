# daily_summary.py
import sqlite3, smtplib, os
from db import DB_PATH

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT   = int(os.getenv("SMTP_PORT","587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
NOTIFY_CC   = os.getenv("NOTIFY_CC")

def daily():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*), status FROM bounces GROUP BY status")
    stats = cur.fetchall()
    con.close()

    body = "Daily Bounce Summary\\n\\n"
    for count, status in stats:
        body += f"{status}: {count}\\n"

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        msg = f"Subject: Daily Bounce Summary\\n\\n{body}"
        server.sendmail(SMTP_USER, NOTIFY_CC, msg)

if __name__ == "__main__":
    daily()