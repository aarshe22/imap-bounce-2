import os
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from db import insert_bounce, init_db
from bounce_rules import classify_bounce

# Load environment variables
load_dotenv("data/.env")

# IMAP Settings
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "143"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
IMAP_SECURE = os.getenv("IMAP_SECURE", "none").lower()  # ssl, starttls, none

# IMAP Folders (normal)
IMAP_FOLDER_INBOX = os.getenv("IMAP_FOLDER_INBOX", "INBOX")
IMAP_FOLDER_PROCESSED = os.getenv("IMAP_FOLDER_PROCESSED", "PROCESSED")
IMAP_FOLDER_PROBLEM = os.getenv("IMAP_FOLDER_PROBLEM", "PROBLEM")
IMAP_FOLDER_SKIPPED = os.getenv("IMAP_FOLDER_SKIPPED", "SKIPPED")

# IMAP Folders (test mode)
IMAP_FOLDER_TEST = os.getenv("IMAP_FOLDER_TEST", "TEST")
IMAP_FOLDER_TESTPROCESSED = os.getenv("IMAP_FOLDER_TESTPROCESSED", "TESTPROCESSED")
IMAP_FOLDER_TESTPROBLEM = os.getenv("IMAP_FOLDER_TESTPROBLEM", "TESTPROBLEM")
IMAP_FOLDER_TESTSKIPPED = os.getenv("IMAP_FOLDER_TESTSKIPPED", "TESTSKIPPED")

# Mode flag
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

# SMTP relay
SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

# Notifications
NOTIFY_CC = os.getenv("NOTIFY_CC", "").split(",")
NOTIFY_CC_TEST = os.getenv("NOTIFY_CC_TEST", "").split(",")


def connect_imap():
    """Establish IMAP connection with SSL or STARTTLS"""
    if IMAP_SECURE == "ssl":
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    else:
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        if IMAP_SECURE == "starttls":
            mail.starttls()
    mail.login(IMAP_USER, IMAP_PASS)
    return mail


def move_message(mail, num, folder):
    """Move message to target folder"""
    try:
        mail.copy(num, folder)
        mail.store(num, "+FLAGS", "\\Deleted")
    except Exception as e:
        print(f"Failed to move message {num} → {folder}: {e}")


def process_mailbox():
    """Connect to IMAP and process bounce emails"""
    init_db()
    try:
        mail = connect_imap()
        inbox = IMAP_FOLDER_TEST if IMAP_TEST_MODE else IMAP_FOLDER_INBOX
        processed = IMAP_FOLDER_TESTPROCESSED if IMAP_TEST_MODE else IMAP_FOLDER_PROCESSED
        problem = IMAP_FOLDER_TESTPROBLEM if IMAP_TEST_MODE else IMAP_FOLDER_PROBLEM
        skipped = IMAP_FOLDER_TESTSKIPPED if IMAP_TEST_MODE else IMAP_FOLDER_SKIPPED

        mail.select(inbox)
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

            # Extract
            msg_to = msg.get("To", "")
            msg_cc = msg.get("Cc", "")
            subject = msg.get("Subject", "")
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

            # Classify bounce
            status, reason, domain = classify_bounce(msg)

            # Save
            insert_bounce(msg_to, msg_cc, status, reason, domain)

            # Notify
            if IMAP_TEST_MODE:
                notify_emails = NOTIFY_CC_TEST
            else:
                notify_emails = [*NOTIFY_CC, *msg_cc.split(",") if msg_cc else []]

            if notify_emails:
                send_notification(subject, msg_to, msg_cc, status, reason, notify_emails)

            # Folder routing
            if status == "failed":
                move_message(mail, num, processed)
            elif status == "unknown":
                move_message(mail, num, skipped)
            else:
                move_message(mail, num, problem)

        mail.expunge()
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
            if SMTP_USER and SMTP_PASS:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(IMAP_USER, notify_emails, msg.as_string())
        print(f"Sent notification to {notify_emails}")
    except Exception as e:
        print("Error sending notification:", str(e))


if __name__ == "__main__":
    process_mailbox()