import sqlite3, os, smtplib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from email.message import EmailMessage
from db import DB_PATH
load_dotenv("/data/.env")
SMTP_SERVER=os.getenv("SMTP_SERVER"); SMTP_PORT=int(os.getenv("SMTP_PORT",587))
SMTP_USER=os.getenv("SMTP_USER"); SMTP_PASS=os.getenv("SMTP_PASS"); NOTIFY_CC=os.getenv("NOTIFY_CC")
def send_summary(body):
    msg=EmailMessage(); msg["From"]=SMTP_USER; msg["To"]=NOTIFY_CC; msg["Subject"]="Daily Bounce Summary"; msg.set_content(body)
    with smtplib.SMTP(SMTP_SERVER,SMTP_PORT) as s: s.starttls(); s.login(SMTP_USER,SMTP_PASS); s.send_message(msg)
def generate_summary():
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    yesterday=(datetime.utcnow()-timedelta(days=1)).isoformat()
    rows=c.execute("SELECT * FROM bounces WHERE timestamp > ?",(yesterday,)).fetchall(); conn.close()
    body=f"Daily Bounce Report ({len(rows)} items)\n\n"
    for r in rows: _,ts,msgid,subject,orig_to,bounced,reason,status=r; body+=f"{ts} | {bounced} | {status} | {reason} | {subject}\n"
    return body
if __name__=="__main__": body=generate_summary(); send_summary(body)
