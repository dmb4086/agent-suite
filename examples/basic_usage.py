"""Basic usage of the Agent Suite SDK.

Demonstrates:
- Creating an inbox
- Sending an email
- Listing messages
- Error handling

Prerequisites:
    pip install agent-suite-sdk
    # or from the repo root:
    pip install ./agent-suite-sdk

    # Start the API server:
    docker-compose up -d
"""

from agent_suite_sdk import (
    AgentSuiteClient,
    AuthenticationError,
    ServiceUnavailableError,
)


def main():
    # ── 1. Create an inbox ────────────────────────────────────────
    client = AgentSuiteClient(base_url="http://localhost:8000")

    print("Creating inbox...")
    inbox = client.create_inbox()
    print(f"  Email:   {inbox.email_address}")
    print(f"  API Key: {inbox.api_key}")
    print(f"  ID:      {inbox.id}")
    print()

    # ── 2. Authenticate with the new API key ──────────────────────
    client = AgentSuiteClient(
        base_url="http://localhost:8000",
        api_key=inbox.api_key,
    )

    # Verify authentication works
    my_inbox = client.get_inbox()
    print(f"Authenticated as: {my_inbox.email_address}")
    print()

    # ── 3. Send an email ──────────────────────────────────────────
    try:
        result = client.send_email(
            to="recipient@example.com",
            subject="Hello from Agent Suite SDK",
            body="This email was sent programmatically using the Python SDK.",
            html_body="<p>This email was sent <b>programmatically</b> using the Python SDK.</p>",
        )
        print(f"Email sent! Message ID: {result.message_id}")
    except ServiceUnavailableError:
        print("AWS SES is not configured — skipping send.")
    print()

    # ── 4. List messages ──────────────────────────────────────────
    messages = client.list_messages(limit=10)
    print(f"Total messages: {messages.total}")
    for msg in messages.messages:
        status = "unread" if not msg.is_read else "read"
        print(f"  [{status}] From: {msg.sender} — {msg.subject}")
    print()

    # ── 5. List unread only ───────────────────────────────────────
    unread = client.list_messages(unread_only=True)
    print(f"Unread messages: {unread.total}")
    print()

    # ── 6. Error handling ─────────────────────────────────────────
    bad_client = AgentSuiteClient(
        base_url="http://localhost:8000",
        api_key="invalid_key",
    )
    try:
        bad_client.get_inbox()
    except AuthenticationError as e:
        print(f"Auth error (expected): {e.message}")

    print("\nDone!")


if __name__ == "__main__":
    main()
