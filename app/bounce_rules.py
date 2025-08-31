# bounce_rules.py
"""
Bounce detection module.
- Uses regex patterns for provider-specific bounce messages.
- Falls back to SMTP status codes (RFC 3463, RFC 5248).
"""

import re, email

# SMTP Status code dictionary
SMTP_STATUS_CODES = {
    "2.1.5": "Recipient address valid",
    "4.2.2": "Mailbox full (quota exceeded)",
    "4.4.1": "Connection timed out",
    "4.4.2": "Bad connection / unable to relay",
    "4.4.7": "Message expired after retries",
    "4.5.3": "Too many recipients",
    "5.0.0": "General failure",
    "5.1.0": "Addressing issue",
    "5.1.1": "Invalid recipient address",
    "5.1.2": "Domain does not exist",
    "5.1.3": "Bad destination mailbox syntax",
    "5.1.6": "Mailbox has moved",
    "5.2.0": "Mailbox disabled",
    "5.2.1": "Mailbox disabled / not accepting",
    "5.2.2": "Mailbox full",
    "5.3.0": "System not accepting network messages",
    "5.3.2": "System not accepting network messages",
    "5.4.1": "No answer from host",
    "5.4.4": "Unable to route",
    "5.4.6": "Routing loop detected",
    "5.5.0": "Invalid command",
    "5.5.2": "Syntax error",
    "5.5.3": "Too many recipients",
    "5.7.1": "Delivery not authorized / blocked / spam",
    "5.7.25": "DMARC validation failed",
    "5.7.26": "SPF validation failed",
    "5.7.27": "DKIM validation failed",
}

# Regex patterns for provider-specific bounces
BOUNCE_PATTERNS = [
    (re.compile(r"user unknown", re.I), "Invalid recipient address"),
    (re.compile(r"no such user", re.I), "Invalid recipient address"),
    (re.compile(r"mailbox full", re.I), "Mailbox full"),
    (re.compile(r"quota exceeded", re.I), "Mailbox full"),
    (re.compile(r"over quota", re.I), "Mailbox full"),
    (re.compile(r"blocked", re.I), "Blocked by provider"),
    (re.compile(r"spam", re.I), "Marked as spam"),
    (re.compile(r"rejected", re.I), "Message rejected"),
    (re.compile(r"not authorized", re.I), "Not authorized"),
    (re.compile(r"policy violation", re.I), "Policy violation"),
]

def detect_bounce(msg):
    """
    Detect whether an email is a bounce message and return (reason, is_bounce).
    Tries in order:
    1. Provider regex patterns
    2. SMTP status codes
    3. DSN (Delivery Status Notification) headers
    """

    # Look into subject line
    subject = msg.get("Subject", "")
    for regex, reason in BOUNCE_PATTERNS:
        if regex.search(subject):
            return reason, True

    # Look into message body
    if msg.is_multipart():
        for part in msg.walk():
            try:
                body = part.get_payload(decode=True).decode(errors="ignore")
            except Exception:
                continue
            for regex, reason in BOUNCE_PATTERNS:
                if regex.search(body):
                    return reason, True
            for code, reason in SMTP_STATUS_CODES.items():
                if code in body:
                    return reason, True
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        except Exception:
            body = ""
        for regex, reason in BOUNCE_PATTERNS:
            if regex.search(body):
                return reason, True
        for code, reason in SMTP_STATUS_CODES.items():
            if code in body:
                return reason, True

    # Fallback: DSN headers
    dsn_action = msg.get("Action")
    dsn_status = msg.get("Status")
    if dsn_action or dsn_status:
        if dsn_status and dsn_status in SMTP_STATUS_CODES:
            return SMTP_STATUS_CODES[dsn_status], True
        elif dsn_action:
            return f"DSN reported action: {dsn_action}", True

    return "Not a bounce", False