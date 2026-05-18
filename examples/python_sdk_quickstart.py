from agentwork_sdk import AgentWorkClient


# Start the API locally first:
# uvicorn app.main:app --reload
with AgentWorkClient(base_url="http://localhost:8000") as client:
    inbox = client.create_inbox()
    print(f"Created inbox: {inbox.email_address}")

    current = client.get_inbox()
    print(f"Current inbox id: {current.id}")

    messages = client.list_messages(limit=10)
    print(f"Messages: {messages.total}")

    # Requires AWS SES settings to be configured on the API server.
    # sent = client.send_email(
    #     to="user@example.com",
    #     subject="Hello from AgentWork",
    #     body="This message was sent via the AgentWork Python SDK.",
    # )
    # print(sent.message_id)
