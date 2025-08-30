# bounce_rules.py
# Dictionaries of SMTP codes, enhanced codes, and provider-specific bounce rules.

SMTP_CODES = {
    "421": "Service not available",
    "450": "Mailbox unavailable",
    "451": "Local error",
    "452": "Insufficient storage",
    "550": "Mailbox unavailable / user not found",
    "552": "Exceeded storage allocation",
    "553": "Mailbox name not allowed",
    "554": "Transaction failed",
}

ENHANCED_CODES = {
    "5.1.1": "Bad destination mailbox address",
    "5.2.2": "Mailbox full",
    "5.7.1": "Delivery not authorized (spam/blocked)",
    "4.2.2": "Mailbox full (temporary)",
}

PROVIDER_RULES = {
    "gmail.com": ["tried to reach does not exist"],
    "outlook.com": ["mailbox unavailable"],
    "yahoo.com": ["doesn't have a yahoo.com account"],
    "icloud.com": ["Mailbox not available"],
}

def classify_bounce(message: str) -> str:
    """Classify bounce message using codes and patterns."""
    for code, desc in ENHANCED_CODES.items():
        if code in message:
            return desc
    for code, desc in SMTP_CODES.items():
        if code in message:
            return desc
    for provider, patterns in PROVIDER_RULES.items():
        for p in patterns:
            if p.lower() in message.lower():
                return f"{provider}: {p}"
    return "Unknown reason"