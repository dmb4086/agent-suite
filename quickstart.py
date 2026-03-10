"""
Quick start example for Agent Suite SDK.

Run: python quickstart.py
"""

from agent_suite_sdk import AgentSuiteClient, Inbox, Email

# Configuration
API_KEY = "your-api-key"  # Or set AGENT_SUITE_API_KEY env var
BASE_URL = "http://localhost:8000"  # Change to production URL


def main():
    print("🤖 Agent Suite SDK - Quick Start\n")
    
    # Initialize client
    client = AgentSuiteClient(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
    # Step 1: Create an inbox
    print("1️⃣ Creating inbox...")
    inbox: Inbox = client.create_inbox()
    print(f"   ✓ Email: {inbox.email_address}")
    print(f"   ✓ ID: {inbox.id}")
    print(f"   ✓ API Key: {inbox.api_key}")
    print("   ⚠️  Save your API key! It's only shown once.\n")
    
    # Step 2: Send an email
    print("2️⃣ Sending email...")
    email: Email = client.send_email(
        inbox_id=inbox.id,
        to="test@example.com",
        subject="Hello from Agent Suite SDK!",
        body="""Hi there!

This email was sent using the Agent Suite Python SDK.

With this SDK, AI agents can:
- Create email inboxes instantly
- Send and receive emails
- Set up webhooks for real-time events

Learn more: https://github.com/dmb4086/agentwork-infrastructure

Best,
Your AI Agent
""",
    )
    print(f"   ✓ Sent! Message ID: {email.id}\n")
    
    # Step 3: List messages
    print("3️⃣ Listing messages...")
    messages = client.list_messages(inbox_id=inbox.id)
    print(f"   ✓ Total messages: {messages.total}")
    for msg in messages.messages:
        print(f"     - {msg.subject} from {msg.from_}\n")
    
    # Step 4: Create a webhook (example)
    print("4️⃣ Creating webhook...")
    webhook = client.create_webhook(
        inbox_id=inbox.id,
        url="https://myapp.com/webhook",
        events=["email.received", "email.sent"],
    )
    print(f"   ✓ Webhook ID: {webhook.id}")
    print(f"   ✓ URL: {webhook.url}\n")
    
    # Clean up
    client.close()
    
    print("🎉 All done! Check your email inbox.")


if __name__ == "__main__":
    main()
