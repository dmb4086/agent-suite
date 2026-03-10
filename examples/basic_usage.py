"""
AgentWork SDK Examples
"""

# Example 1: Async usage
import asyncio
from agent_suite_sdk import AgentWorkClient

async def async_example():
    """Using async client"""

    async with AgentWorkClient() as client:
        # Create a new inbox (no API key needed)
        inbox = await client.create_inbox()
        print(f"📧 Inbox created: {inbox.email_address}")
        print(f"🔑 API Key: {inbox.api_key}")

        # Set the API key for subsequent operations
        client.api_key = inbox.api_key

        # Send an email
        result = await client.send_email(
            to="recipient@example.com",
            subject="Hello from AgentWork SDK",
            body="This is a test email sent using the Python SDK!"
        )
        print(f"✅ Email sent: {result}")

        # List messages
        messages = await client.list_messages()
        for msg in messages:
            print(f"📨 From: {msg.from_email}")
            print(f"   Subject: {msg.subject}")
            print(f"   Body: {msg.body[:50]}...")


# Example 2: Sync usage
from agent_suite_sdk import AgentWorkClientSync

def sync_example():
    """Using sync client"""

    client = AgentWorkClientSync(api_key="your-api-key")

    # List messages
    messages = client.list_messages()
    for msg in messages:
        print(f"Message: {msg.subject}")

    # Send email
    client.send_email(
        to="recipient@example.com",
        subject="Test",
        body="Hello!"
    )

    client.close()


# Example 3: With error handling
async def robust_example():
    """With error handling and retries"""

    client = AgentWorkClient(
        api_key="your-api-key",
        timeout=30.0,
        max_retries=3
    )

    try:
        messages = await client.list_messages()
        print(f"Found {len(messages)} messages")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


# Example 4: Calendar integration
async def calendar_example():
    """Using calendar features"""

    async with AgentWorkClient(api_key="your-api-key") as client:
        # Create event
        event = await client.create_event(
            title="Team Meeting",
            start_time="2026-03-15T10:00:00Z",
            end_time="2026-03-15T11:00:00Z",
            description="Weekly standup"
        )
        print(f"📅 Event created: {event['id']}")

        # List events
        events = await client.list_events()
        for evt in events:
            print(f"📅 {evt['title']} - {evt['start_time']}")


# Run examples
if __name__ == "__main__":
    print("Running async example...")
    asyncio.run(async_example())

    print("\nRunning sync example...")
    sync_example()
