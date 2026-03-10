import asyncio
import os
from agent_suite_sdk import AgentSuiteClient

async def main():
    api_key = os.getenv("AGENT_SUITE_API_KEY", "demo_key")
    client = AgentSuiteClient(api_key=api_key)

    print("Creating inbox...")
    inbox = await client.create_inbox(name="agent_ops_inbox")
    print(f"Created inbox: {inbox.id} ({inbox.address})")

    print("Sending email...")
    await client.send_email(
        to="user@example.com",
        subject="Update from Agent",
        body="Task execution completed successfully."
    )
    print("Email sent!")

    print("Listing messages...")
    messages = await client.list_messages(inbox_id=inbox.id)
    for msg in messages:
        print(f"- {msg.subject}")

    print("Receiving webhook simulation...")
    await client.receive_webhook({
        "event_type": "task.completed",
        "data": {"task_id": "12345", "status": "success"}
    })
    print("Webhook processed.")

if __name__ == "__main__":
    asyncio.run(main())
