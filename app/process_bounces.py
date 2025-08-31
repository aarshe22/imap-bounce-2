# process_bounces.py
import os, imaplib, smtplib, sqlite3, traceback
from email.message import EmailMessage
from dotenv import load_dotenv
from db import log_bounce, update_status, init_db
from bounce_rules import detect_bounce
import mailparser

load_dotenv()
DB_PATH = "/data/bounces.db"

# IMAP config
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
IMAP_SECURE = os.getenv("IMAP_SECURE", "ssl").lower()

# IMAP folders (normal mode)
IMAP_FOLDER_INBOX = os.getenv("IMAP_FOLDER_INBOX", "INBOX")
IMAP_FOLDER_PROCESSED = os.getenv("IMAP_FOLDER_PROCESSED", "PROCESSED")
IMAP_FOLDER_PROBLEM = os.getenv("IMAP_FOLDER_PROBLEM", "PROBLEM")
IMAP_FOLDER_SKIPPED = os.getenv("IMAP_FOLDER_SKIPPED", "SKIPPED")

# IMAP folders (test mode)
IMAP_FOLDER_TEST = os.getenv("IMAP_FOLDER_TEST", "TEST")
IMAP_FOLDER_TESTPROCESSED = os.getenv("IMAP_FOLDER_TESTPROCESSED", "TESTPROCESSED")
IMAP_FOLDER_TESTPROBLEM = os.getenv("IMAP_FOLDER_TESTPROBLEM", "TESTPROBLEM")
IMAP_FOLDER_TESTSKIPPED = os.getenv("IMAP_FOLDER_TESTSKIPPED", "TESTSKIPPED")

# Bounce notification recipients
NOTIFY_CC = [x.strip() for x in os.getenv("NOTIFY_CC", "").split(",") if x.strip()]
NOTIFY_CC_TEST = [x.strip() for x in os.getenv("NOTIFY_CC_TEST", "").split(",") if x.strip()]
IMAP_TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"

SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))

# Ensure DB schema exists
init_db()

def send_notification(to_addrs, original_to, original_cc, reason):
    """Send a bounce notification to the recipients."""
    msg = EmailMessage()
    msg["Subject"] = f"Bounce detected: {original_to}"
    msg["From"] = "bounce-processor@localhost"
    msg["To"] = ", ".join(to_addrs)

    cc_display = ", ".join(original_cc) if original_cc else "None"
    msg.set_content(f"""
A bounced email was detected.

Original To: {original_to}
Original Cc: {cc_display}
Reason: {reason}
""")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.send_message(msg)

def move_message(mail, num, dest_folder):
    """Move IMAP message to destination folder."""
    try:
        mail.copy(num, dest_folder)
        mail.store(num, '+FLAGS', '\\Deleted')
    except Exception:
        traceback.print_exc()

def process_mail():
    """Main loop to process bounces in the IMAP inbox."""
    if IMAP_SECURE == "starttls":
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.starttls()
    else:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

    mail.login(IMAP_USER, IMAP_PASS)

    # Select source folder (INBOX vs TEST)
    if IMAP_TEST_MODE:
        folder_inbox = IMAP_FOLDER_TEST
        folder_processed = IMAP_FOLDER_TESTPROCESSED
        folder_problem = IMAP_FOLDER_TESTPROBLEM
        folder_skipped = IMAP_FOLDER_TESTSKIPPED
    else:
        folder_inbox = IMAP_FOLDER_INBOX
        folder_processed = IMAP_FOLDER_PROCESSED
        folder_problem = IMAP_FOLDER_PROBLEM
        folder_skipped = IMAP_FOLDER_SKIPPED

    mail.select(folder_inbox)
    status, data = mail.search(None, "ALL")
    if status != "OK":
        print("No messages found.")
        return

    for num in data[0].split():
        try:
            typ, msg_data = mail.fetch(num, "(RFC822)")
            raw_email = msg_data[0][1]

            # Try parsing with mailparser
            try:
                parsed = mailparser.parse_from_bytes(raw_email)
                to_list = [addr for addr in parsed.to_] if parsed.to_ else []
                cc_list = [addr for addr in parsed.cc_] if parsed.cc_ else []
                subject = parsed.subject or ""
                msg_obj = parsed.message
            except Exception:
                import email
                msg_obj = email.message_from_bytes(raw_email)
                to_list = [addr for _, addr in email.utils.getaddresses(msg_obj.get_all("To", []))]
                cc_list = [addr for _, addr in email.utils.getaddresses(msg_obj.get_all("Cc", []))]
                subject = msg_obj.get("Subject", "")

            # Detect bounce
            reason, is_bounce = detect_bounce(msg_obj)

            if is_bounce:
                for addr in to_list:
                    log_bounce(msg_obj.get("Date"), addr, ",".join(cc_list), "Processed", reason, addr.split("@")[-1])

                # Decide notification recipients
                if IMAP_TEST_MODE:
                    notify_recipients = NOTIFY_CC_TEST
                else:
                    notify_recipients = NOTIFY_CC + cc_list

                if notify_recipients:
                    send_notification(notify_recipients, ",".join(to_list), cc_list, reason)

                move_message(mail, num, folder_processed)

            else:
                for addr in to_list:
                    log_bounce(msg_obj.get("Date"), addr, ",".join(cc_list), "Skipped", "Not a bounce", addr.split("@")[-1])
                move_message(mail, num, folder_skipped)

        except Exception:
            traceback.print_exc()
            try:
                move_message(mail, num, folder_problem)
            except Exception:
                traceback.print_exc()

    mail.expunge()
    mail.logout()

if __name__ == "__main__":
    process_mail()