"""Agent Suite SDK — Python client for the Agent Suite API.

Infrastructure for agents, by agents. No human OAuth required.

Usage:
    from agent_suite_sdk import AgentSuiteClient

    client = AgentSuiteClient(base_url="http://localhost:8000")

    # Create an inbox
    inbox = client.create_inbox()
    print(inbox.email_address, inbox.api_key)

    # Authenticate and use the inbox
    client = AgentSuiteClient(
        base_url="http://localhost:8000",
        api_key=inbox.api_key,
    )
    messages = client.list_messages()
"""

from agent_suite_sdk.client import AgentSuiteClient, AsyncAgentSuiteClient
from agent_suite_sdk.models import (
    Inbox,
    InboxPublic,
    MessageCreate,
    MessageResponse,
    MessageList,
    SendResponse,
    WebhookPayload,
    WebhookResponse,
)
from agent_suite_sdk.exceptions import (
    AgentSuiteError,
    AuthenticationError,
    NotFoundError,
    ServerError,
    ServiceUnavailableError,
    RateLimitError,
)

__version__ = "0.1.0"
__all__ = [
    "AgentSuiteClient",
    "AsyncAgentSuiteClient",
    "Inbox",
    "InboxPublic",
    "MessageCreate",
    "MessageResponse",
    "MessageList",
    "SendResponse",
    "WebhookPayload",
    "WebhookResponse",
    "AgentSuiteError",
    "AuthenticationError",
    "NotFoundError",
    "ServerError",
    "ServiceUnavailableError",
    "RateLimitError",
]
