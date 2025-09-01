import os
import imaplib
import email
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
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

# Jinja2 template environment
TEMPLATE_ENV = Environment(loader=FileSystemLoader("docs/templates"))

# SMTP status code → description map
SMTP_DESCRIPTIONS = {
    "421": "Service not available, try again later (often temporary)",
    "450": "Mailbox unavailable (server busy or mailbox locked)",
    "451": "Requested action aborted – local error in processing",
    "452": "Insufficient system storage – mailbox is full",
    "500": "Syntax error, command unrecognized",
    "501": "Syntax error in parameters or arguments",
    "502": "Command not implemented by this server",
    "503": "Bad sequence of commands",
    "504": "Command parameter not implemented",
    "550": "Mailbox unavailable – recipient address rejected",
    "551": "User not local – please try forwarding",
    "552": "Exceeded storage allocation – mailbox is full",
    "553": "Mailbox name not allowed – invalid syntax or format",
    "554": "Transaction failed – message rejected as spam or blocked"
}


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

        # Org info
        "ORG_NAME": os.getenv("ORG_NAME", "Support Team"),
        "ORG_EMAIL": os.getenv("ORG_EMAIL", "support@example.com"),
        "ORG_LOGO_URL": os.getenv("ORG_LOGO_URL", "")
    }
    return config


def extract_original_recipients(msg):
    """Try to pull the original To/Cc from embedded message/rfc822 part"""
    orig_to, orig_cc = "", ""
    try:
        for part in msg.walk():
            if part.get_content_type() == "message/rfc822":
                logger.debug("[DEBUG] Found embedded original message/rfc822 part")
                payload = part.get_payload()
                if isinstance(payload, list) and len(payload) > 0:
                    embedded = payload[0]
                    orig_to = embedded.get("To", "")
                    orig_cc = embedded.get("Cc", "")
                    logger.debug(f"[DEBUG] Extracted from embedded: To={orig_to}, Cc={orig_cc}")
                    break
    except Exception as e:
        logger.error(f"[DEBUG] Error extracting embedded original: {e}")
    return orig_to, orig_cc


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

            # Default headers from the bounce
            bounce_to = msg.get("To", "")
            bounce_cc = msg.get("Cc", "")
            subject = msg.get("Subject", "")
            logger.debug(f"[DEBUG] Bounce headers: To={bounce_to}, Cc={bounce_cc}, Subject={subject}")

            # Try to extract the real original recipients
            orig_to, orig_cc = extract_original_recipients(msg)
            if not orig_to and not orig_cc:
                logger.debug("[DEBUG] Fallback: No embedded original found, using bounce headers")
                orig_to, orig_cc = bounce_to, bounce_cc

            # Classify bounce
            status, reason, domain = classify_bounce(msg)
            logger.debug(f"[DEBUG] Classification: status={status}, reason={reason}, domain={domain}")

            # Determine notification recipients
            if config["IMAP_TEST_MODE"]:
                notified_to = config["NOTIFY_CC_TEST"]
                notified_cc = []
            else:
                notified_to = [e.strip() for e in orig_cc.split(",") if e.strip()]
                notified_cc = config["NOTIFY_CC"]

            # Save into DB
            insert_bounce(orig_to, orig_cc, status, reason, domain,
                          notified_to=",".join(notified_to),
                          notified_cc=",".join(notified_cc))

            # Send notification
            if notified_to or notified_cc:
                send_notification(config, subject, orig_to, orig_cc, status, reason, notified_to, notified_cc)

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