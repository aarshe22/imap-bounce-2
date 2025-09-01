import os
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from db import insert_bounce, init_db
from bounce_rules import classify_bounce

# Load environment variables
load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))

NOTIFY_CC = os.getenv("NOTIFY_CC", "").split(",")
NOTIFY_CC_TEST = os.getenv("NOTIFY_CC_TEST", "").split(",")
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"


def process_mailbox():
    """Connect to IMAP and process bounce emails"""
    init_db()

    try:
        # Support "host:port" in IMAP_SERVER
        host, port = IMAP_SERVER.split(":") if ":" in IMAP_SERVER else (IMAP_SERVER, 143)
        mail = imaplib.IMAP4(host, int(port))
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("INBOX")

        result, data = mail.search(None, "ALL")
        if result != "OK":
            print("No messages found!")
            return

        for num in data[0].split():
            result, msg_data = mail.fetch(num, "(RFC822)")
            if result != "OK":
                print("Error fetching message", num)
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract fields
            msg_to = msg.get("To", "")
            msg_cc = msg.get("Cc", "")
            subject = msg.get("Subject", "")

            # Classify bounce (pass full email.message.Message)
            status, reason, domain = classify_bounce(msg)

            # Save to DB
            insert_bounce(msg_to, msg_cc, status, reason, domain)

            # Notify logic
            if IMAP_TEST_MODE:
                notify_emails = [n for n in NOTIFY_CC_TEST if n]
            else:
                cc_list = [c.strip() for c in msg_cc.split(",")] if msg_cc else []
                notify_emails = [*NOTIFY_CC, *cc_list]
                notify_emails = [n for n in notify_emails if n]

            if notify_emails:
                send_notification(subject, msg_to, msg_cc, status, reason, notify_emails)

            # Mark processed
            mail.store(num, "+FLAGS", "\\Seen")

        mail.logout()

    except Exception as e:
        print("Error processing mailbox:", str(e))


def send_notification(subject, to_addr, cc_addr, status, reason, notify_emails):
    """Send bounce notification email"""
    msg = MIMEText(
        f"Bounce detected\n\nTo: {to_addr}\nCc: {cc_addr}\nStatus: {status}\nReason: {reason}"
    )
    msg["Subject"] = f"Bounce Notification: {status}"
    msg["From"] = IMAP_USER
    msg["To"] = ", ".join(notify_emails)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.sendmail(IMAP_USER, notify_emails, msg.as_string())
        print(f"Sent notification to {notify_emails}")
    except Exception as e:
        print("Error sending notification:", str(e))


if __name__ == "__main__":
    process_mailbox()