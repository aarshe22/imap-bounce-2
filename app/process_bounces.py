import os
import imaplib
import email
import smtplib
import logging
from email.mime.text import MIMEText
from dotenv import load_dotenv
from db import insert_bounce, init_db
from bounce_rules import classify_bounce

# ============================================
# Setup logging
# ============================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s"
)
logger = logging.getLogger("process_bounces")

ENV_FILE = "data/.env"

def load_config():
    """Reload config from .env each run (supports real-time toggle)"""
    load_dotenv(ENV_FILE, override=True)

    config = {
        # IMAP
        "IMAP_SERVER": os.getenv("IMAP_SERVER"),
        "IMAP_PORT": int(os.getenv("IMAP_PORT", "143")),
        "IMAP_USER": os.getenv("IMAP_USER"),
        "IMAP_PASS": os.getenv("IMAP_PASS"),
        "IMAP_SECURE": os.getenv("IMAP_SECURE", "none").lower(),

        # IMAP Folders (normal)
        "IMAP_FOLDER_INBOX": os.getenv("IMAP_FOLDER_INBOX", "INBOX"),
        "IMAP_FOLDER_PROCESSED": os.getenv("IMAP_FOLDER_PROCESSED", "PROCESSED"),
        "IMAP_FOLDER_PROBLEM": os.getenv("IMAP_FOLDER_PROBLEM", "PROBLEM"),
        "IMAP_FOLDER_SKIPPED": os.getenv("IMAP_FOLDER_SKIPPED", "SKIPPED"),

        # IMAP Folders (test mode)
        "IMAP_FOLDER_TEST": os.getenv("IMAP_FOLDER_TEST", "TEST"),
        "IMAP_FOLDER_TESTPROCESSED": os.getenv("IMAP_FOLDER_TESTPROCESSED", "TESTPROCESSED"),
        "IMAP_FOLDER_TESTPROBLEM": os.getenv("IMAP_FOLDER_TESTPROBLEM", "TESTPROBLEM"),
        "IMAP_FOLDER_TESTSKIPPED": os.getenv("IMAP_FOLDER_TESTSKIPPED", "TESTSKIPPED"),

        # Flags
        "IMAP_TEST_MODE": os.getenv("IMAP_TEST_MODE", "false").lower() == "true",

        # SMTP
        "SMTP_SERVER": os.getenv("SMTP_SERVER", "localhost"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "25")),
        "SMTP_USER": os.getenv("SMTP_USER", ""),
        "SMTP_PASS": os.getenv("SMTP_PASS", ""),

        # Notifications
        "NOTIFY_CC": [e.strip() for e in os.getenv("NOTIFY_CC", "").split(",") if e.strip()],
        "NOTIFY_CC_TEST": [e.strip() for e in os.getenv("NOTIFY_CC_TEST", "").split(",") if e.strip()],
    }
    return config

def connect_imap(config):
    """Establish IMAP connection with SSL or STARTTLS"""
    logger.debug(f"[DEBUG] Connecting to IMAP {config['IMAP_SERVER']}:{config['IMAP_PORT']} secure={config['IMAP_SECURE']}")
    if config["IMAP_SECURE"] == "ssl":
        mail = imaplib.IMAP4_SSL(config["IMAP_SERVER"], config["IMAP_PORT"])
    else:
        mail = imaplib.IMAP4(config["IMAP_SERVER"], config["IMAP_PORT"])
        if config["IMAP_SECURE"] == "starttls":
            mail.starttls()
    mail.login(config["IMAP_USER"], config["IMAP_PASS"])
    logger.debug("[DEBUG] IMAP login successful")
    return mail

def move_message(mail, num, folder):
    """Move message to target folder"""
    try:
        mail.copy(num, folder)
        mail.store(num, "+FLAGS", "\\Deleted")
        logger.debug(f"[DEBUG] Moving message {num} → {folder}")
    except Exception as e:
        logger.error(f"Failed to move message {num} → {folder}: {e}")

def process_mailbox():
    """Connect to IMAP and process bounce emails"""
    config = load_config()
    init_db()

    try:
        mail = connect_imap(config)

        if config["IMAP_TEST_MODE"]:
            inbox = config["IMAP_FOLDER_TEST"]
            processed = config["IMAP_FOLDER_TESTPROCESSED"]
            problem = config["IMAP_FOLDER_TESTPROBLEM"]
            skipped = config["IMAP_FOLDER_TESTSKIPPED"]
            logger.debug("[DEBUG] Running in TEST MODE")
        else:
            inbox = config["IMAP_FOLDER_INBOX"]
            processed = config["IMAP_FOLDER_PROCESSED"]
            problem = config["IMAP_FOLDER_PROBLEM"]
            skipped = config["IMAP_FOLDER_SKIPPED"]
            logger.debug("[DEBUG] Running in NORMAL MODE")

        mail.select(inbox)
        result, data = mail.search(None, "ALL")
        if result != "OK":
            logger.warning("No messages found!")
            return

        logger.debug(f"[DEBUG] Found {len(data[0].split())} messages")

        for num in data[0].split():
            logger.debug(f"[DEBUG] Fetching message {num.decode()}")
            result, msg_data = mail.fetch(num, "(RFC822)")
            if result != "OK":
                logger.warning(f"Error fetching message {num}")
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract
            msg_to = msg.get("To", "")
            msg_cc = msg.get("Cc", "")
            subject = msg.get("Subject", "")
            logger.debug(f"[DEBUG] Processing message: To={msg_to}, Cc={msg_cc}, Subject={subject}")

            # Classify bounce
            status, reason, domain = classify_bounce(msg)
            logger.debug(f"[DEBUG] Classification: status={status}, reason={reason}, domain={domain}")

            # Save
            insert_bounce(msg_to, msg_cc, status, reason, domain)

            # Notify
            if config["IMAP_TEST_MODE"]:
                notify_emails = config["NOTIFY_CC_TEST"]
                logger.debug(f"[DEBUG] Test mode: notifying {notify_emails}")
            else:
                notify_emails = config["NOTIFY_CC"] + ([e.strip() for e in msg_cc.split(",")] if msg_cc else [])
                logger.debug(f"[DEBUG] Normal mode: notifying {notify_emails}")

            if notify_emails:
                send_notification(config, subject, msg_to, msg_cc, status, reason, notify_emails)

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
        logger.error("Error processing mailbox: %s", str(e))

def send_notification(config, subject, to_addr, cc_addr, status, reason, notify_emails):
    """Send bounce notification email"""
    msg = MIMEText(
        f"Bounce detected\n\nTo: {to_addr}\nCc: {cc_addr}\nStatus: {status}\nReason: {reason}"
    )
    msg["Subject"] = f"Bounce Notification: {status}"
    msg["From"] = config["IMAP_USER"]
    msg["To"] = ", ".join(notify_emails)

    try:
        with smtplib.SMTP(config["SMTP_SERVER"], config["SMTP_PORT"]) as server:
            if config["SMTP_USER"] and config["SMTP_PASS"]:
                server.starttls()
                server.login(config["SMTP_USER"], config["SMTP_PASS"])
            logger.debug(f"[DEBUG] Sending notification to {notify_emails}")
            server.sendmail(config["IMAP_USER"], notify_emails, msg.as_string())
        print(f"Sent notification to {notify_emails}")
    except Exception as e:
        logger.error("Error sending notification: %s", str(e))

if __name__ == "__main__":
    process_mailbox()