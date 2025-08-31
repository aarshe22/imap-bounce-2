# process_bounces.py
import os, imaplib, email
from email.header import decode_header
from datetime import datetime
from dotenv import load_dotenv
from db import init_db, log_bounce
from bounce_rules import classify_bounce

load_dotenv()
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER   = os.getenv("IMAP_USER")
IMAP_PASS   = os.getenv("IMAP_PASS")
IMAP_PORT   = int(os.getenv("IMAP_PORT", "993"))
IMAP_SECURE = os.getenv("IMAP_SECURE", "ssl").lower()
TEST_MODE   = os.getenv("IMAP_TEST_MODE","false").lower() == "true"

# Folders
INBOX      = os.getenv("IMAP_FOLDER_TEST" if TEST_MODE else "IMAP_FOLDER_INBOX")
PROCESSED  = os.getenv("IMAP_FOLDER_TESTPROCESSED" if TEST_MODE else "IMAP_FOLDER_PROCESSED")
PROBLEM    = os.getenv("IMAP_FOLDER_TESTPROBLEM" if TEST_MODE else "IMAP_FOLDER_PROBLEM")
SKIPPED    = os.getenv("IMAP_FOLDER_TESTSKIPPED" if TEST_MODE else "IMAP_FOLDER_SKIPPED")

def connect_imap():
    if IMAP_SECURE == "ssl":
        return imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    elif IMAP_SECURE == "starttls":
        conn = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        conn.starttls()
        return conn
    else:
        return imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)

def process():
    init_db()
    mail = connect_imap()
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select(INBOX)

    typ, data = mail.search(None, "ALL")
    for num in data[0].split():
        typ, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        # Decode subject
        subject, enc = decode_header(msg.get("Subject",""))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(enc or "utf-8", errors="ignore")

        # Extract plain body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                    except Exception:
                        body = ""
                    break
        else:
            try:
                body = msg.get_payload(decode=True).decode(errors="ignore")
            except Exception:
                body = ""

        # Extract top-level To and CC headers
        to_addr = msg.get_all("To", []) or []
        cc_addr = msg.get_all("Cc", []) or []
        to_str = ", ".join(to_addr)
        cc_str = ", ".join(cc_addr)

        reason = classify_bounce(subject + " " + body)
        date = datetime.utcnow().isoformat()
        domain = to_str.split("@")[-1] if "@" in to_str else "unknown"

        if "Unknown" not in reason:
            log_bounce(date, to_str, cc_str, "Processed", reason, domain)
            mail.copy(num, PROCESSED)
        else:
            log_bounce(date, to_str, cc_str, "Skipped", reason, domain)
            mail.copy(num, SKIPPED)

        mail.store(num, "+FLAGS", "\\\\Deleted")

    mail.expunge()
    mail.logout()

if __name__ == "__main__":
    process()