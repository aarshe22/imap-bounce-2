import os
import imaplib
import email
import re
import smtplib
from email.mime.text import MIMEText
from db import log_bounce
from bounce_patterns import BOUNCE_PATTERNS

IMAP_SERVER   = os.getenv("IMAP_SERVER")
IMAP_USER     = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
SMTP_SERVER   = os.getenv("SMTP_SERVER", "localhost")
NOTIFY_CC     = os.getenv("NOTIFY_CC", "").split(",")
NOTIFY_CC_TEST = os.getenv("NOTIFY_CC_TEST", "").split(",")
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"


def connect_imap():
    server, port = (IMAP_SERVER.split(":") + ["143"])[:2]
    M = imaplib.IMAP4(server, int(port))
    M.login(IMAP_USER, IMAP_PASSWORD)
    return M


def extract_status_and_reason(body):
    for pattern, status, reason in BOUNCE_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return status, reason
    return "unknown", "Unrecognized bounce format"


def send_notification(original_to, original_cc, status, reason):
    recipients = []
    if IMAP_TEST_MODE:
        recipients = NOTIFY_CC_TEST
    else:
        if original_cc:
            recipients.extend(original_cc)
        recipients.extend(NOTIFY_CC)

    recipients = [r.strip() for r in recipients if r.strip()]
    if not recipients:
        return

    subject = f"Bounce detected for {original_to} - {status}"
    body = f"""
    A bounce was detected.

    To: {original_to}
    CC: {", ".join(original_cc) if original_cc else "(none)"}
    Status: {status}
    Reason: {reason}
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = IMAP_USER
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(SMTP_SERVER) as s:
        s.sendmail(IMAP_USER, recipients, msg.as_string())


def process_bounces():
    M = connect_imap()
    M.select("INBOX")
    typ, data = M.search(None, "UNSEEN")
    for num in data[0].split():
        typ, msg_data = M.fetch(num, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        original_to = msg.get("To", "")
        original_cc = msg.get_all("Cc", [])

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        status, reason = extract_status_and_reason(body)

        # persist
        log_bounce(original_to, original_cc, status, reason)

        # notify
        send_notification(original_to, original_cc, status, reason)

        # mark as seen
        M.store(num, "+FLAGS", "\\Seen")
    M.close()
    M.logout()


if __name__ == "__main__":
    process_bounces()