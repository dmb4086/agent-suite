"""Webhook proxy example using the Agent Suite SDK.

Demonstrates:
- Parsing incoming webhook data
- Forwarding webhooks via the SDK
- Using WebhookPayload model for validation

This example shows how to receive Mailgun webhooks in your own
service and forward them to Agent Suite. Useful when you need
to add custom processing (filtering, logging, enrichment) before
the message reaches Agent Suite.

Prerequisites:
    pip install agent-suite-sdk fastapi uvicorn
    docker-compose up -d
"""

from fastapi import FastAPI, Form
from typing import Optional

from agent_suite_sdk import AgentSuiteClient, WebhookPayload

proxy_app = FastAPI(title="Webhook Proxy")

# Point to the Agent Suite API
suite_client = AgentSuiteClient(base_url="http://localhost:8000")


@proxy_app.post("/webhooks/incoming")
def handle_incoming_email(
    sender: str = Form(...),
    recipient: str = Form(...),
    subject: str = Form(default=""),
    body_plain: str = Form(default="", alias="body-plain"),
    body_html: str = Form(default="", alias="body-html"),
    message_id: str = Form(default="", alias="Message-Id"),
):
    """Receive a webhook, validate it, then forward to Agent Suite."""

    # ── 1. Parse and validate the payload ─────────────────────────
    payload = WebhookPayload(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
        message_id=message_id,
    )

    # ── 2. Custom processing (optional) ───────────────────────────
    # Example: Log, filter spam, enrich with metadata, etc.
    print(f"Incoming: {payload.sender} -> {payload.recipient}: {payload.subject}")

    if "unsubscribe" in payload.subject.lower():
        print("  Filtered: unsubscribe request — not forwarding.")
        return {"status": "filtered", "reason": "unsubscribe"}

    # ── 3. Forward to Agent Suite ─────────────────────────────────
    result = suite_client.receive_webhook(payload)
    print(f"  Forwarded: status={result.status}")

    return {"status": result.status, "message_id": result.message_id}


if __name__ == "__main__":
    import uvicorn

    print("Starting webhook proxy on http://localhost:9000")
    print("Configure Mailgun to POST to: http://your-server:9000/webhooks/incoming")
    uvicorn.run(proxy_app, host="0.0.0.0", port=9000)
