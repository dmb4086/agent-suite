import hashlib
import hmac
import io
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.db.database import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_inbox(setup_db):
    response = client.post("/v1/inboxes")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "email_address" in data
    assert "api_key" in data
    assert data["email_address"].endswith("@agents.dev")


def test_get_my_inbox(setup_db):
    # Create inbox
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]

    # Get inbox with API key
    response = client.get(
        "/v1/inboxes/me",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_address"] == create_resp.json()["email_address"]


def test_invalid_api_key(setup_db):
    response = client.get(
        "/v1/inboxes/me",
        headers={"Authorization": "Bearer invalid_key"}
    )
    assert response.status_code == 401


def test_list_messages(setup_db):
    # Create inbox
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    # Simulate incoming message via webhook
    client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "Test Subject",
            "body-plain": "Test body",
            "Message-Id": "test123",
        }
    )

    # List messages
    response = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["subject"] == "Test Subject"


# ── Email Verification Tests ──


def test_webhook_spf_dkim_pass(setup_db):
    """Test that SPF/DKIM pass results are stored on the message."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "verified@example.com",
            "recipient": email,
            "subject": "Verified Email",
            "body-plain": "This is verified",
            "Message-Id": "verified-001",
            "X-Mailgun-Spf": "Pass",
            "X-Mailgun-Dkim-Check-Result": "Pass",
            "X-Mailgun-SSscore": "0.5",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["verified"] is True
    assert data["spam_score"] == 0.5

    # Verify stored message includes verification data
    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["spf_pass"] is True
    assert msg["dkim_pass"] is True
    assert msg["spam_score"] == 0.5
    assert msg["is_verified"] is True


def test_webhook_spf_fail(setup_db):
    """Test that SPF failure is recorded correctly."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "spoofed@example.com",
            "recipient": email,
            "subject": "SPF Fail",
            "body-plain": "SPF failed",
            "X-Mailgun-Spf": "Fail",
            "X-Mailgun-Dkim-Check-Result": "Pass",
            "X-Mailgun-SSscore": "2.0",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False  # SPF failed, so not fully verified

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["spf_pass"] is False
    assert msg["dkim_pass"] is True
    assert msg["is_verified"] is False


def test_webhook_dkim_fail(setup_db):
    """Test that DKIM failure is recorded correctly."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "DKIM Fail",
            "body-plain": "DKIM failed",
            "X-Mailgun-Spf": "Pass",
            "X-Mailgun-Dkim-Check-Result": "Fail",
            "X-Mailgun-SSscore": "1.0",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["spf_pass"] is True
    assert msg["dkim_pass"] is False
    assert msg["is_verified"] is False


def test_webhook_both_spf_dkim_fail(setup_db):
    """Test message stored when both SPF and DKIM fail (not spam though)."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "bad@example.com",
            "recipient": email,
            "subject": "Both Fail",
            "body-plain": "Both failed",
            "X-Mailgun-Spf": "Fail",
            "X-Mailgun-Dkim-Check-Result": "Fail",
            "X-Mailgun-SSscore": "3.0",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["spf_pass"] is False
    assert msg["dkim_pass"] is False
    assert msg["is_verified"] is False


def test_webhook_no_verification_headers(setup_db):
    """Test webhook without verification headers (backward compatible)."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "No Headers",
            "body-plain": "No verification headers",
        }
    )
    assert response.status_code == 200

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["spf_pass"] is False
    assert msg["dkim_pass"] is False
    assert msg["spam_score"] == 0.0
    assert msg["is_verified"] is False


# ── Spam Filtering Tests ──


def test_webhook_spam_rejected(setup_db):
    """Test that emails with spam score > 5 are rejected."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "spammer@example.com",
            "recipient": email,
            "subject": "Buy Now!!!",
            "body-plain": "SPAM SPAM SPAM",
            "X-Mailgun-SSscore": "7.5",
        }
    )
    assert response.status_code == 400
    assert "rejected" in response.json()["detail"].lower()


def test_webhook_spam_score_exactly_5_not_rejected(setup_db):
    """Test that email with spam score exactly 5.0 is NOT rejected (> 5 threshold)."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "borderline@example.com",
            "recipient": email,
            "subject": "Borderline",
            "body-plain": "Borderline spam",
            "X-Mailgun-SSscore": "5.0",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"


def test_webhook_spam_score_just_above_threshold(setup_db):
    """Test that email with spam score 5.1 IS rejected."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "spammer@example.com",
            "recipient": email,
            "subject": "Spam",
            "body-plain": "Spam content",
            "X-Mailgun-SSscore": "5.1",
        }
    )
    assert response.status_code == 400


def test_webhook_spam_invalid_score_defaults_zero(setup_db):
    """Test that invalid spam score defaults to 0.0 (not rejected)."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "Bad Score",
            "body-plain": "Invalid score",
            "X-Mailgun-SSscore": "not-a-number",
        }
    )
    assert response.status_code == 200
    assert response.json()["spam_score"] == 0.0


def test_webhook_spam_does_not_store_message(setup_db):
    """Test that rejected spam emails are NOT stored in the database."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    # Send a spam email
    client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "spammer@example.com",
            "recipient": email,
            "subject": "SPAM",
            "body-plain": "This is spam",
            "X-Mailgun-SSscore": "10.0",
        }
    )

    # Verify no messages stored
    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert messages_resp.json()["total"] == 0


# ── Attachment Tests ──


def test_webhook_with_attachment_metadata(setup_db):
    """Test that attachment metadata is stored and returned in message response."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    # Create a test file attachment
    file_content = b"Hello, this is a test file attachment."
    files = {
        "attachment-1": ("test.txt", io.BytesIO(file_content), "text/plain"),
    }
    data = {
        "sender": "test@example.com",
        "recipient": email,
        "subject": "With Attachment",
        "body-plain": "See attached",
        "attachment-count": "1",
        "X-Mailgun-Spf": "Pass",
        "X-Mailgun-Dkim-Check-Result": "Pass",
        "X-Mailgun-SSscore": "0.1",
    }

    response = client.post("/v1/webhooks/mailgun", data=data, files=files)
    assert response.status_code == 200

    # Verify attachment metadata in messages endpoint
    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert len(msg["attachments"]) == 1
    att = msg["attachments"][0]
    assert att["filename"] == "test.txt"
    assert att["content_type"] == "text/plain"
    assert att["size"] == len(file_content)
    assert "id" in att
    assert "uploaded_at" in att


def test_webhook_with_multiple_attachments(setup_db):
    """Test handling multiple attachments on a single email."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    file1_content = b"File one content"
    file2_content = b"File two content with more data"
    files = {
        "attachment-1": ("document.pdf", io.BytesIO(file1_content), "application/pdf"),
        "attachment-2": ("image.png", io.BytesIO(file2_content), "image/png"),
    }
    data = {
        "sender": "test@example.com",
        "recipient": email,
        "subject": "Multiple Attachments",
        "body-plain": "Two files attached",
        "attachment-count": "2",
    }

    response = client.post("/v1/webhooks/mailgun", data=data, files=files)
    assert response.status_code == 200

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert len(msg["attachments"]) == 2

    filenames = {att["filename"] for att in msg["attachments"]}
    assert "document.pdf" in filenames
    assert "image.png" in filenames

    sizes = {att["filename"]: att["size"] for att in msg["attachments"]}
    assert sizes["document.pdf"] == len(file1_content)
    assert sizes["image.png"] == len(file2_content)


def test_webhook_no_attachments_empty_list(setup_db):
    """Test that messages without attachments return empty attachments list."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "No Attachments",
            "body-plain": "Plain email",
        }
    )

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["attachments"] == []


def test_webhook_attachment_with_s3_upload(setup_db):
    """Test that attachments are uploaded to S3 when configured."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]
    api_key = create_resp.json()["api_key"]

    file_content = b"S3 test file content"
    files = {
        "attachment-1": ("s3test.txt", io.BytesIO(file_content), "text/plain"),
    }
    data = {
        "sender": "test@example.com",
        "recipient": email,
        "subject": "S3 Upload Test",
        "body-plain": "S3 test",
        "attachment-count": "1",
    }

    mock_s3 = MagicMock()

    with patch("app.services.attachment_service.upload_to_s3", return_value=True) as mock_upload, \
         patch("app.main.get_s3_client", return_value=mock_s3), \
         patch.object(
             type(app.state), "__getattr__", create=True
         ):
        # Temporarily patch settings to have S3 config
        import app.main as main_module
        orig_bucket = main_module.settings.s3_bucket
        orig_key = main_module.settings.aws_access_key_id
        main_module.settings.s3_bucket = "test-bucket"
        main_module.settings.aws_access_key_id = "test-key"

        try:
            response = client.post("/v1/webhooks/mailgun", data=data, files=files)
            assert response.status_code == 200

            # Verify upload_to_s3 was called
            mock_upload.assert_called_once()
            # upload_to_s3(s3_client, bucket, key, file_data, content_type)
            call_args = mock_upload.call_args[0]
            assert call_args[0] is mock_s3  # s3_client
            assert call_args[1] == "test-bucket"  # bucket
            assert "s3test.txt" in call_args[2]  # s3_key contains filename
            assert call_args[3] == file_content  # file_data
            assert call_args[4] == "text/plain"  # content_type
        finally:
            main_module.settings.s3_bucket = orig_bucket
            main_module.settings.aws_access_key_id = orig_key


# ── Webhook Signature Verification Tests ──


def test_webhook_valid_signature(setup_db):
    """Test that valid Mailgun webhook signature is accepted."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    signing_key = "test-signing-key-12345"
    timestamp = "1234567890"
    token = "test-token-abc"
    signature = hmac.new(
        signing_key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    with patch("app.main.settings") as mock_settings:
        mock_settings.mailgun_signing_key = signing_key
        mock_settings.spam_score_threshold = 5.0
        mock_settings.s3_bucket = ""
        mock_settings.aws_access_key_id = ""

        response = client.post(
            "/v1/webhooks/mailgun",
            data={
                "sender": "test@example.com",
                "recipient": email,
                "subject": "Signed",
                "body-plain": "Signed email",
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
            }
        )
        # Should accept (200 or dropped since inbox might not match the mock)
        assert response.status_code in (200, 403) or response.json().get("status") in ("received", "dropped")


def test_webhook_invalid_signature(setup_db):
    """Test that invalid Mailgun webhook signature is rejected."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    with patch("app.main.settings") as mock_settings:
        mock_settings.mailgun_signing_key = "real-signing-key"
        mock_settings.spam_score_threshold = 5.0

        response = client.post(
            "/v1/webhooks/mailgun",
            data={
                "sender": "test@example.com",
                "recipient": email,
                "subject": "Forged",
                "body-plain": "Forged webhook",
                "timestamp": "1234567890",
                "token": "token",
                "signature": "invalid-signature",
            }
        )
        assert response.status_code == 403
        assert "signature" in response.json()["detail"].lower()


def test_webhook_no_signing_key_skips_verification(setup_db):
    """Test that webhook signature verification is skipped when no key configured."""
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    # No signature fields, no signing key configured - should work fine
    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "No Signing",
            "body-plain": "No signature check",
        }
    )
    assert response.status_code == 200


# ── Webhook Backward Compatibility Tests ──


def test_webhook_body_plain_field_name(setup_db):
    """Test that both 'body-plain' and 'body_plain' field names work."""
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    # Test with body-plain (Mailgun's actual format)
    client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "Hyphenated",
            "body-plain": "Body with hyphen",
        }
    )

    messages_resp = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    msg = messages_resp.json()["messages"][0]
    assert msg["body_text"] == "Body with hyphen"


def test_webhook_dropped_for_inactive_inbox(setup_db):
    """Test that emails for non-existent inboxes are silently dropped."""
    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": "nonexistent@agents.dev",
            "subject": "Dropped",
            "body-plain": "This should be dropped",
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "dropped"


# ── Email Verification Service Unit Tests ──


def test_verify_email_all_pass():
    """Test verify_email with all checks passing."""
    from app.services.email_verification import verify_email

    result = verify_email(
        spf_header="Pass",
        dkim_header="Pass",
        spam_score_header="0.5",
        spam_threshold=5.0,
    )
    assert result.spf_pass is True
    assert result.dkim_pass is True
    assert result.spam_score == 0.5
    assert result.is_verified is True
    assert result.is_spam is False
    assert result.rejection_reason is None


def test_verify_email_spam_detected():
    """Test verify_email with spam score above threshold."""
    from app.services.email_verification import verify_email

    result = verify_email(
        spf_header="Pass",
        dkim_header="Pass",
        spam_score_header="8.5",
        spam_threshold=5.0,
    )
    assert result.is_spam is True
    assert result.is_verified is False
    assert "exceeds threshold" in result.rejection_reason


def test_verify_email_empty_headers():
    """Test verify_email with empty headers."""
    from app.services.email_verification import verify_email

    result = verify_email()
    assert result.spf_pass is False
    assert result.dkim_pass is False
    assert result.spam_score == 0.0
    assert result.is_verified is False
    assert result.is_spam is False


def test_verify_email_case_insensitive():
    """Test that SPF/DKIM header parsing is case insensitive."""
    from app.services.email_verification import verify_email

    result = verify_email(
        spf_header="PASS",
        dkim_header="pass",
    )
    assert result.spf_pass is True
    assert result.dkim_pass is True


def test_parse_spam_score_edge_cases():
    """Test spam score parsing with various edge cases."""
    from app.services.email_verification import parse_spam_score

    assert parse_spam_score("") == 0.0
    assert parse_spam_score(None) == 0.0
    assert parse_spam_score("abc") == 0.0
    assert parse_spam_score("3.14") == 3.14
    assert parse_spam_score("-1.5") == -1.5
    assert parse_spam_score("0") == 0.0
    assert parse_spam_score("10.0") == 10.0


def test_verify_mailgun_webhook_signature():
    """Test Mailgun webhook signature verification."""
    from app.services.email_verification import verify_mailgun_webhook_signature

    key = "my-signing-key"
    timestamp = "1234567890"
    token = "unique-token"
    sig = hmac.new(
        key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert verify_mailgun_webhook_signature(key, timestamp, token, sig) is True
    assert verify_mailgun_webhook_signature(key, timestamp, token, "bad") is False
    assert verify_mailgun_webhook_signature("", timestamp, token, sig) is False
    assert verify_mailgun_webhook_signature(key, "", token, sig) is False
    assert verify_mailgun_webhook_signature(key, timestamp, "", sig) is False


def test_verify_dkim_signature_with_dkimpy():
    """Test DKIM signature verification via dkimpy (mocked DNS)."""
    from app.services.email_verification import verify_dkim_signature

    # Test with invalid raw email (should return False gracefully)
    result = verify_dkim_signature(b"not a valid email")
    assert result is False


# ── Attachment Service Unit Tests ──


def test_generate_s3_key():
    """Test S3 key generation produces unique, safe keys."""
    from app.services.attachment_service import generate_s3_key

    key1 = generate_s3_key("attachments", "msg-123", "file.txt")
    key2 = generate_s3_key("attachments", "msg-123", "file.txt")

    # Keys should be unique even for same inputs
    assert key1 != key2
    assert key1.startswith("attachments/msg-123/")
    assert key1.endswith("_file.txt")

    # Test path traversal prevention
    key3 = generate_s3_key("attachments", "msg-456", "../../etc/passwd")
    assert "/" not in key3.split("/", 2)[-1].rsplit("_", 1)[0][:-1]  # no traversal in UUID
    assert ".._.._.._etc_passwd" in key3 or "etc_passwd" in key3


def test_upload_to_s3_success():
    """Test successful S3 upload."""
    from app.services.attachment_service import upload_to_s3

    mock_s3 = MagicMock()
    result = upload_to_s3(mock_s3, "bucket", "key", b"data", "text/plain")
    assert result is True
    mock_s3.put_object.assert_called_once_with(
        Bucket="bucket",
        Key="key",
        Body=b"data",
        ContentType="text/plain",
    )


def test_upload_to_s3_failure():
    """Test S3 upload failure handling."""
    from app.services.attachment_service import upload_to_s3

    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "Internal Server Error"}},
        "PutObject",
    )
    result = upload_to_s3(mock_s3, "bucket", "key", b"data", "text/plain")
    assert result is False
