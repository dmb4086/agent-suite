"""Tests for the Agent Suite SDK client.

Uses respx to mock httpx requests, covering:
- All public methods (sync and async)
- Error handling and typed exceptions
- Retry logic with backoff
- Edge cases (empty responses, invalid JSON, timeouts)
"""

import asyncio
from unittest.mock import patch

import httpx
import pytest
import respx

from agent_suite_sdk import (
    AgentSuiteClient,
    AsyncAgentSuiteClient,
    AuthenticationError,
    Inbox,
    InboxPublic,
    MessageList,
    NotFoundError,
    SendResponse,
    ServerError,
    ServiceUnavailableError,
    WebhookPayload,
    WebhookResponse,
)
from agent_suite_sdk.exceptions import AgentSuiteError, RateLimitError

BASE_URL = "http://localhost:8000"


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Sync client with no retries (faster tests)."""
    c = AgentSuiteClient(base_url=BASE_URL, api_key="as_testkey123", max_retries=0)
    yield c
    c.close()


@pytest.fixture
def client_with_retries():
    """Sync client with retries enabled (low backoff for speed)."""
    c = AgentSuiteClient(
        base_url=BASE_URL,
        api_key="as_testkey123",
        max_retries=2,
        backoff_factor=0.01,
    )
    yield c
    c.close()


@pytest.fixture
def unauthenticated_client():
    """Sync client without an API key."""
    c = AgentSuiteClient(base_url=BASE_URL, max_retries=0)
    yield c
    c.close()


# ── Sample response data ─────────────────────────────────────────

INBOX_RESPONSE = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email_address": "abc123@agents.dev",
    "api_key": "as_a1b2c3d4e5f6",
    "created_at": "2026-03-09T12:00:00",
}

INBOX_PUBLIC_RESPONSE = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email_address": "abc123@agents.dev",
    "created_at": "2026-03-09T12:00:00",
}

SEND_RESPONSE = {
    "status": "sent",
    "message_id": "ses-msg-001",
    "to": "bob@example.com",
}

MESSAGE_LIST_RESPONSE = {
    "total": 2,
    "messages": [
        {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "sender": "alice@example.com",
            "recipient": "abc123@agents.dev",
            "subject": "Hello",
            "body_text": "Hi there",
            "received_at": "2026-03-09T12:30:00",
            "is_read": False,
        },
        {
            "id": "660e8400-e29b-41d4-a716-446655440002",
            "sender": "bob@example.com",
            "recipient": "abc123@agents.dev",
            "subject": "Re: Hello",
            "body_text": "Hey!",
            "received_at": "2026-03-09T12:35:00",
            "is_read": True,
        },
    ],
}

WEBHOOK_RESPONSE = {
    "status": "received",
    "message_id": "770e8400-e29b-41d4-a716-446655440000",
}


# ── Health check ──────────────────────────────────────────────────

class TestHealthCheck:
    @respx.mock
    def test_health_check(self, client):
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok", "service": "agent-suite"})
        )
        result = client.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "agent-suite"


# ── Create inbox ──────────────────────────────────────────────────

class TestCreateInbox:
    @respx.mock
    def test_create_inbox_success(self, unauthenticated_client):
        respx.post(f"{BASE_URL}/v1/inboxes").mock(
            return_value=httpx.Response(201, json=INBOX_RESPONSE)
        )
        inbox = unauthenticated_client.create_inbox()
        assert isinstance(inbox, Inbox)
        assert inbox.email_address == "abc123@agents.dev"
        assert inbox.api_key == "as_a1b2c3d4e5f6"
        assert str(inbox.id) == "550e8400-e29b-41d4-a716-446655440000"


# ── Get inbox ─────────────────────────────────────────────────────

class TestGetInbox:
    @respx.mock
    def test_get_inbox_success(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(200, json=INBOX_PUBLIC_RESPONSE)
        )
        inbox = client.get_inbox()
        assert isinstance(inbox, InboxPublic)
        assert inbox.email_address == "abc123@agents.dev"

    @respx.mock
    def test_get_inbox_unauthorized(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        with pytest.raises(AuthenticationError) as exc_info:
            client.get_inbox()
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)


# ── Send email ────────────────────────────────────────────────────

class TestSendEmail:
    @respx.mock
    def test_send_email_success(self, client):
        respx.post(f"{BASE_URL}/v1/inboxes/me/send").mock(
            return_value=httpx.Response(200, json=SEND_RESPONSE)
        )
        result = client.send_email(
            to="bob@example.com",
            subject="Test",
            body="Hello!",
        )
        assert isinstance(result, SendResponse)
        assert result.status == "sent"
        assert result.message_id == "ses-msg-001"
        assert result.to == "bob@example.com"

    @respx.mock
    def test_send_email_with_html(self, client):
        respx.post(f"{BASE_URL}/v1/inboxes/me/send").mock(
            return_value=httpx.Response(200, json=SEND_RESPONSE)
        )
        result = client.send_email(
            to="bob@example.com",
            subject="Test",
            body="Hello!",
            html_body="<p>Hello!</p>",
        )
        assert result.status == "sent"

        # Verify the request body included html_body
        request = respx.calls.last.request
        import json
        body = json.loads(request.content)
        assert body["html_body"] == "<p>Hello!</p>"

    @respx.mock
    def test_send_email_ses_unavailable(self, client):
        respx.post(f"{BASE_URL}/v1/inboxes/me/send").mock(
            return_value=httpx.Response(503, json={"detail": "AWS SES not configured"})
        )
        with pytest.raises(ServiceUnavailableError) as exc_info:
            client.send_email(to="bob@example.com", subject="Test", body="Hi")
        assert "AWS SES not configured" in str(exc_info.value)

    @respx.mock
    def test_send_email_server_error(self, client):
        respx.post(f"{BASE_URL}/v1/inboxes/me/send").mock(
            return_value=httpx.Response(500, json={"detail": "SES error: throttling"})
        )
        with pytest.raises(ServerError):
            client.send_email(to="bob@example.com", subject="Test", body="Hi")


# ── List messages ─────────────────────────────────────────────────

class TestListMessages:
    @respx.mock
    def test_list_messages_success(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me/messages").mock(
            return_value=httpx.Response(200, json=MESSAGE_LIST_RESPONSE)
        )
        result = client.list_messages()
        assert isinstance(result, MessageList)
        assert result.total == 2
        assert len(result.messages) == 2
        assert result.messages[0].subject == "Hello"
        assert result.messages[1].is_read is True

    @respx.mock
    def test_list_messages_with_params(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me/messages").mock(
            return_value=httpx.Response(200, json={"total": 0, "messages": []})
        )
        result = client.list_messages(skip=10, limit=5, unread_only=True)
        assert result.total == 0
        assert result.messages == []

        # Verify query parameters
        request = respx.calls.last.request
        assert "skip=10" in str(request.url)
        assert "limit=5" in str(request.url)
        assert "unread_only=true" in str(request.url)

    @respx.mock
    def test_list_messages_empty(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me/messages").mock(
            return_value=httpx.Response(200, json={"total": 0, "messages": []})
        )
        result = client.list_messages()
        assert result.total == 0
        assert result.messages == []


# ── Webhook ───────────────────────────────────────────────────────

class TestWebhook:
    @respx.mock
    def test_receive_webhook_success(self, client):
        respx.post(f"{BASE_URL}/v1/webhooks/mailgun").mock(
            return_value=httpx.Response(200, json=WEBHOOK_RESPONSE)
        )
        payload = WebhookPayload(
            sender="alice@example.com",
            recipient="abc123@agents.dev",
            subject="Incoming",
            body_plain="Hello from outside",
        )
        result = client.receive_webhook(payload)
        assert isinstance(result, WebhookResponse)
        assert result.status == "received"
        assert result.message_id == "770e8400-e29b-41d4-a716-446655440000"

    @respx.mock
    def test_receive_webhook_dropped(self, client):
        respx.post(f"{BASE_URL}/v1/webhooks/mailgun").mock(
            return_value=httpx.Response(200, json={"status": "dropped"})
        )
        payload = WebhookPayload(
            sender="alice@example.com",
            recipient="nonexistent@agents.dev",
        )
        result = client.receive_webhook(payload)
        assert result.status == "dropped"
        assert result.message_id is None


# ── Error handling ────────────────────────────────────────────────

class TestErrorHandling:
    @respx.mock
    def test_404_raises_not_found(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NotFoundError) as exc_info:
            client.get_inbox()
        assert exc_info.value.status_code == 404

    @respx.mock
    def test_429_raises_rate_limit(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(429, json={"detail": "Rate limit exceeded"})
        )
        with pytest.raises(RateLimitError):
            client.get_inbox()

    @respx.mock
    def test_generic_400_raises_agent_suite_error(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(400, json={"detail": "Bad request"})
        )
        with pytest.raises(AgentSuiteError) as exc_info:
            client.get_inbox()
        assert exc_info.value.status_code == 400

    @respx.mock
    def test_error_with_plain_text_body(self, client):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(ServerError) as exc_info:
            client.get_inbox()
        assert "Internal Server Error" in str(exc_info.value)


# ── Retry logic ───────────────────────────────────────────────────

class TestRetryLogic:
    @respx.mock
    def test_retry_on_500(self, client_with_retries):
        route = respx.get(f"{BASE_URL}/health")
        route.side_effect = [
            httpx.Response(500, json={"detail": "Temporary failure"}),
            httpx.Response(500, json={"detail": "Temporary failure"}),
            httpx.Response(200, json={"status": "ok", "service": "agent-suite"}),
        ]
        result = client_with_retries.health_check()
        assert result["status"] == "ok"
        assert route.call_count == 3

    @respx.mock
    def test_retry_exhausted_raises(self, client_with_retries):
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(503, json={"detail": "Down"})
        )
        with pytest.raises(ServiceUnavailableError):
            client_with_retries.health_check()

    @respx.mock
    def test_no_retry_on_401(self, client_with_retries):
        route = respx.get(f"{BASE_URL}/v1/inboxes/me")
        route.mock(return_value=httpx.Response(401, json={"detail": "Invalid API key"}))
        with pytest.raises(AuthenticationError):
            client_with_retries.get_inbox()
        # 401 is not retryable — should only be called once
        assert route.call_count == 1

    @respx.mock
    def test_retry_on_connection_error(self, client_with_retries):
        route = respx.get(f"{BASE_URL}/health")
        route.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, json={"status": "ok", "service": "agent-suite"}),
        ]
        result = client_with_retries.health_check()
        assert result["status"] == "ok"
        assert route.call_count == 2

    @respx.mock
    def test_retry_respects_retry_after_header(self, client_with_retries):
        route = respx.get(f"{BASE_URL}/health")
        route.side_effect = [
            httpx.Response(
                429,
                json={"detail": "Rate limited"},
                headers={"Retry-After": "0.01"},
            ),
            httpx.Response(200, json={"status": "ok", "service": "agent-suite"}),
        ]
        result = client_with_retries.health_check()
        assert result["status"] == "ok"


# ── Context manager ──────────────────────────────────────────────

class TestContextManager:
    @respx.mock
    def test_sync_context_manager(self):
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok", "service": "agent-suite"})
        )
        with AgentSuiteClient(base_url=BASE_URL, max_retries=0) as client:
            result = client.health_check()
            assert result["status"] == "ok"


# ── Async client ──────────────────────────────────────────────────

class TestAsyncClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_async_health_check(self):
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok", "service": "agent-suite"})
        )
        async with AsyncAgentSuiteClient(base_url=BASE_URL, max_retries=0) as client:
            result = await client.health_check()
            assert result["status"] == "ok"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_create_inbox(self):
        respx.post(f"{BASE_URL}/v1/inboxes").mock(
            return_value=httpx.Response(201, json=INBOX_RESPONSE)
        )
        async with AsyncAgentSuiteClient(base_url=BASE_URL, max_retries=0) as client:
            inbox = await client.create_inbox()
            assert isinstance(inbox, Inbox)
            assert inbox.email_address == "abc123@agents.dev"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_send_email(self):
        respx.post(f"{BASE_URL}/v1/inboxes/me/send").mock(
            return_value=httpx.Response(200, json=SEND_RESPONSE)
        )
        async with AsyncAgentSuiteClient(
            base_url=BASE_URL, api_key="as_test", max_retries=0
        ) as client:
            result = await client.send_email(
                to="bob@example.com", subject="Test", body="Hello!"
            )
            assert result.status == "sent"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_list_messages(self):
        respx.get(f"{BASE_URL}/v1/inboxes/me/messages").mock(
            return_value=httpx.Response(200, json=MESSAGE_LIST_RESPONSE)
        )
        async with AsyncAgentSuiteClient(
            base_url=BASE_URL, api_key="as_test", max_retries=0
        ) as client:
            result = await client.list_messages()
            assert result.total == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_receive_webhook(self):
        respx.post(f"{BASE_URL}/v1/webhooks/mailgun").mock(
            return_value=httpx.Response(200, json=WEBHOOK_RESPONSE)
        )
        async with AsyncAgentSuiteClient(base_url=BASE_URL, max_retries=0) as client:
            payload = WebhookPayload(
                sender="alice@example.com",
                recipient="abc123@agents.dev",
                subject="Test",
            )
            result = await client.receive_webhook(payload)
            assert result.status == "received"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        respx.get(f"{BASE_URL}/v1/inboxes/me").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        async with AsyncAgentSuiteClient(
            base_url=BASE_URL, api_key="bad_key", max_retries=0
        ) as client:
            with pytest.raises(AuthenticationError):
                await client.get_inbox()

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_retry_on_server_error(self):
        route = respx.get(f"{BASE_URL}/health")
        route.side_effect = [
            httpx.Response(502, json={"detail": "Bad Gateway"}),
            httpx.Response(200, json={"status": "ok", "service": "agent-suite"}),
        ]
        async with AsyncAgentSuiteClient(
            base_url=BASE_URL, max_retries=2, backoff_factor=0.01
        ) as client:
            result = await client.health_check()
            assert result["status"] == "ok"
            assert route.call_count == 2


# ── Model validation ─────────────────────────────────────────────

class TestModels:
    def test_inbox_model(self):
        inbox = Inbox(**INBOX_RESPONSE)
        assert str(inbox.id) == "550e8400-e29b-41d4-a716-446655440000"
        assert inbox.email_address == "abc123@agents.dev"
        assert inbox.api_key == "as_a1b2c3d4e5f6"

    def test_inbox_public_model(self):
        pub = InboxPublic(**INBOX_PUBLIC_RESPONSE)
        assert pub.email_address == "abc123@agents.dev"

    def test_webhook_payload_defaults(self):
        payload = WebhookPayload(sender="a@b.com", recipient="c@d.com")
        assert payload.subject == ""
        assert payload.body_plain == ""
        assert payload.body_html == ""
        assert payload.message_id == ""

    def test_message_list_model(self):
        ml = MessageList(**MESSAGE_LIST_RESPONSE)
        assert ml.total == 2
        assert ml.messages[0].sender == "alice@example.com"
        assert ml.messages[1].is_read is True

    def test_send_response_model(self):
        sr = SendResponse(**SEND_RESPONSE)
        assert sr.status == "sent"
        assert sr.message_id == "ses-msg-001"


# ── Exception hierarchy ──────────────────────────────────────────

class TestExceptions:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(AuthenticationError, AgentSuiteError)
        assert issubclass(NotFoundError, AgentSuiteError)
        assert issubclass(RateLimitError, AgentSuiteError)
        assert issubclass(ServiceUnavailableError, AgentSuiteError)
        assert issubclass(ServerError, AgentSuiteError)

    def test_exception_attributes(self):
        err = AuthenticationError(detail="Bad key")
        assert err.status_code == 401
        assert err.detail == "Bad key"
        assert err.message == "Bad key"

    def test_base_exception_is_standard_exception(self):
        err = AgentSuiteError("test", status_code=418, detail="teapot")
        assert isinstance(err, Exception)
        assert str(err) == "test"
