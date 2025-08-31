import os
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from db import log_bounce
from bounce_patterns import classify_bounce

# Environment variables
IMAP_SERVER      = os.getenv("IMAP_SERVER")
IMAP_USER        = os.getenv("IMAP_USER")
IMAP_PASS        = os.getenv("IMAP_PASS")
NOTIFY_CC        = os.getenv("NOTIFY_CC", "")
NOTIFY_CC_TEST   = os.getenv("NOTIFY_CC_TEST", "")
IMAP_TEST_MODE   = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

def connect_imap():
    """Connect and return IMAP connection."""
    host, port = (IMAP_SERVER.split(":") + ["993"])[:2]
    port = int(port)
    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(IMAP_USER, IMAP_PASS)
    return conn

def process_bounces():
    """Main IMAP loop to find and process bounce emails."""
    conn = connect_imap()
    conn.select("INBOX")

    # Search all unseen messages
    status, messages = conn.search(None, '(UNSEEN)')
    if status != "OK":
        print("No messages found.")
        return

    for num in messages[0].split():
        res, msg_data = conn.fetch(num, "(RFC822)")
        if res != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject, encoding = decode_header(msg.get("Subject"))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")

        email_to = msg.get("To", "")
        email_cc = msg.get("Cc", "")

        # Classify bounce reason
        reason, status = classify_bounce(subject + " " + str(msg))

        # Log bounce into SQLite
        log_bounce(email_to, email_cc, status, reason)

        # Determine recipients for notifications
        if IMAP_TEST_MODE:
            notify_recipients = NOTIFY_CC_TEST.split(",") if NOTIFY_CC_TEST else []
        else:
            notify_recipients = []
            if email_cc:
                notify_recipients += [c.strip() for c in email_cc.split(",")]
            if NOTIFY_CC:
                notify_recipients += [c.strip() for c in NOTIFY_CC.split(",")]

        # Send notifications
        if notify_recipients:
            send_notification(email_to, email_cc, reason, notify_recipients)

        # Mark processed
        conn.store(num, '+FLAGS', '\\Seen')

    conn.close()
    conn.logout()

def send_notification(email_to, email_cc, reason, recipients):
    """Send bounce notification to recipients."""
    body = f"""Bounce detected:
To: {email_to}
CC: {email_cc}
Reason: {reason}
"""
    msg = MIMEText(body)
    msg["Subject"] = "Bounce Notification"
    msg["From"] = IMAP_USER
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP("localhost") as server:
            server.sendmail(IMAP_USER, recipients, msg.as_string())
            print(f"Notification sent to {recipients}")
    except Exception as e:
        print(f"Error sending notification: {e}")

if __name__ == "__main__":
    process_bounces()