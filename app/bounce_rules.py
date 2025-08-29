COMMON_PATTERNS = {
    "550": "Mailbox unavailable",
    "user unknown": "Invalid recipient",
    "mailbox full": "Mailbox full",
    "spam": "Rejected as spam"
}
PROVIDER_RULES = {
    "outlook.com": {"5.1.10": "Invalid address format","5.2.2": "Mailbox full"},
    "gmail.com": {"no such user": "Invalid Gmail account"},
    "yahoo.com": {"user not found": "Invalid Yahoo account"}
}
def match_reason(domain, body):
    text = body.lower()
    for k,v in COMMON_PATTERNS.items():
        if k in text: return v
    if domain in PROVIDER_RULES:
        for k,v in PROVIDER_RULES[domain].items():
            if k in text: return v
    return "Unknown"
