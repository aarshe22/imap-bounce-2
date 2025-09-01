from bounce_rules import classify_bounce

# Some fake bounce samples for testing
TEST_BOUNCES = [
    {
        "subject": "Mail delivery failed: returning message to sender",
        "body": "550 5.1.1 <user@nowhere.com>: Recipient address rejected: User unknown in virtual mailbox table",
    },
    {
        "subject": "Undelivered Mail Returned to Sender",
        "body": "The recipient's mailbox is full. Please try again later. user@example.org",
    },
    {
        "subject": "Delivery Status Notification (Failure)",
        "body": "Host or domain name not found. Name service error for name=invalid-domain.tld",
    },
    {
        "subject": "Message blocked",
        "body": "Your message to test@corp.com was blocked due to blacklisted content",
    },
    {
        "subject": "Mail rejected as spam",
        "body": "This message was marked as spam and has been rejected by our filters. test@spamtrap.net",
    },
    {
        "subject": "Temporary error",
        "body": "451 4.3.0 Resources temporarily unavailable. Please try again later. foo@bar.net",
    },
    {
        "subject": "Weird failure",
        "body": "Strange bounce text with no obvious reason. user@unknownhost",
    },
]

if __name__ == "__main__":
    print("Running bounce rule classification tests...\n")

    for i, sample in enumerate(TEST_BOUNCES, 1):
        status, reason, domain = classify_bounce(sample["body"], sample["subject"])
        print(f"Test {i}:")
        print(f"  Subject : {sample['subject']}")
        print(f"  Body    : {sample['body'][:80]}...")
        print(f"  Result  : status={status}, reason={reason}, domain={domain}")
        print("-" * 60)