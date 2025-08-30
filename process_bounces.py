#!/usr/bin/env python3
import imaplib, os, smtplib, logging
from email.header import decode_header, make_header
from email.message import EmailMessage
from dotenv import load_dotenv
from mailparser import parse_from_bytes
from db import init_db, log_bounce
from bounce_rules import match_reason
from retry_queue import enqueue_retry

load_dotenv("/data/.env")
init_db()

# Load env
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER   = os.getenv("IMAP_USER")
IMAP_PASS   = os.getenv("IMAP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT   = int(os.getenv("SMTP_PORT", 587))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
NOTIFY_CC   = os.getenv("NOTIFY_CC")

# Folder mappings (normal vs test mode)
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"
IMAP_FOLDER_INBOX      = os.getenv("IMAP_FOLDER_TEST" if IMAP_TEST_MODE else "IMAP_FOLDER_INBOX", "INBOX")
IMAP_FOLDER_PROCESSED  = os.getenv("IMAP_FOLDER_TESTPROCESSED" if IMAP_TEST_MODE else "IMAP_FOLDER_PROCESSED", "PROCESSED")
IMAP_FOLDER_PROBLEM    = os.getenv("IMAP_FOLDER_TESTPROBLEM" if IMAP_TEST_MODE else "IMAP_FOLDER_PROBLEM", "PROBLEM")
IMAP_FOLDER_SKIPPED    = os.getenv("IMAP_FOLDER_TESTSKIPPED" if IMAP_TEST_MODE else "IMAP_FOLDER_SKIPPED", "SKIPPED")

logging.basicConfig(filename="/data/bounce_processor.log", level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")

def decode_mime(s): 
    return str(make_header(decode_header(s or "")))

def send_notification(bounced_email, subject, reason, cc):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = cc
    msg["Subject"] = f"[Bounce] Delivery failed to {bounced_email}"
    body = f"Delivery to {bounced_email} failed.\n\nSubject: {subject}\nReason: {reason}\n"
    msg.set_content(body)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def process_bounces():
    conn = imaplib.IMAP4_SSL(IMAP_SERVER)
    conn.login(IMAP_USER, IMAP_PASS)
    conn.select(IMAP_FOLDER_INBOX)

    typ, data = conn.search(None, 'UNSEEN')
    if typ != "OK": 
        return

    for num in data[0].split():
        typ, msg_data = conn.fetch(num, "(RFC822)")
        raw = msg_data[0][1]
        mail = parse_from_bytes(raw)
        subject = decode_mime(mail.subject)
        msgid = mail.message_id
        body_text = "\n".join(mail.text_plain or [])

        bounced_email, reason = "", ""
        headers = mail.headers

        # Try to extract bounce details
        if "Final-Recipient" in headers:
            bounced_email = headers["Final-Recipient"].split(";")[-1].strip()
            reason = headers.get("Diagnostic-Code", "")
        else:
            for line in body_text.splitlines():
                if "550" in line or "user unknown" in line.lower():
                    bounced_email = line.split()[-1].strip("<>")
                    reason = line.strip()
                    break

        # Process
        if bounced_email:
            reason = match_reason(bounced_email.split("@")[-1], body_text)
            try:
                send_notification(bounced_email, subject, reason, NOTIFY_CC)
                log_bounce(msgid, subject, "", bounced_email, reason, "PROCESSED")
                conn.copy(num, IMAP_FOLDER_PROCESSED)
            except Exception:
                enqueue_retry(num.decode(), bounced_email, subject, reason, NOTIFY_CC)
                log_bounce(msgid, subject, "", bounced_email, reason, "FAILED")
                conn.copy(num, IMAP_FOLDER_PROBLEM)
        else:
            log_bounce(msgid, subject, "", "", "Not a bounce", "SKIPPED")
            conn.copy(num, IMAP_FOLDER_SKIPPED)

        conn.store(num, '+FLAGS', '\\Deleted')

    conn.expunge()
    conn.close()
    conn.logout()

if __name__ == "__main__":
    process_bounces()