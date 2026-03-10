"""Async usage of the Agent Suite SDK.

Demonstrates:
- Using the async client with asyncio
- Concurrent operations
- Context manager pattern

Prerequisites:
    pip install agent-suite-sdk
    docker-compose up -d
"""

import asyncio

from agent_suite_sdk import AsyncAgentSuiteClient, ServiceUnavailableError


async def main():
    # ── 1. Create an inbox (no auth needed) ───────────────────────
    async with AsyncAgentSuiteClient(base_url="http://localhost:8000") as client:
        print("Creating inbox...")
        inbox = await client.create_inbox()
        print(f"  Email:   {inbox.email_address}")
        print(f"  API Key: {inbox.api_key}")
        print()

    # ── 2. Use the inbox with the API key ─────────────────────────
    async with AsyncAgentSuiteClient(
        base_url="http://localhost:8000",
        api_key=inbox.api_key,
    ) as client:

        # Run multiple operations concurrently
        inbox_info, messages = await asyncio.gather(
            client.get_inbox(),
            client.list_messages(),
        )

        print(f"Inbox: {inbox_info.email_address}")
        print(f"Messages: {messages.total}")
        print()

        # ── 3. Send email (if SES is configured) ─────────────────
        try:
            result = await client.send_email(
                to="agent@example.com",
                subject="Async hello",
                body="Sent from the async SDK client!",
            )
            print(f"Sent! ID: {result.message_id}")
        except ServiceUnavailableError:
            print("SES not configured — skipping send.")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
