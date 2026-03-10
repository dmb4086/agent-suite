import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.db.database import Base

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
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]

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
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "test@example.com",
            "recipient": email,
            "subject": "Test Subject",
            "body_plain": "Test body",
            "message_id": "test123",
            "dkim": "pass",
            "SPF": "pass",
            "spam_score": "1.5",
        }
    )

    response = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["subject"] == "Test Subject"
    assert data["messages"][0]["dkim_passed"] is True
    assert data["messages"][0]["spf_passed"] is True
    assert data["messages"][0]["spam_score"] == "1.5"


def test_reject_spam_message(setup_db):
    create_resp = client.post("/v1/inboxes")
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "spam@example.com",
            "recipient": email,
            "subject": "Spam",
            "body_plain": "Buy now",
            "message_id": "spam123",
            "spam_score": "8.4",
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reason"] == "spam"


def test_attachment_metadata_is_returned(setup_db):
    create_resp = client.post("/v1/inboxes")
    api_key = create_resp.json()["api_key"]
    email = create_resp.json()["email_address"]

    response = client.post(
        "/v1/webhooks/mailgun",
        data={
            "sender": "files@example.com",
            "recipient": email,
            "subject": "Files",
            "body_plain": "See attachment",
            "message_id": "file123",
            "dkim": "pass",
            "SPF": "pass",
            "spam_score": "0.2",
        },
        files={
            "attachment_1": ("hello.txt", io.BytesIO(b"hello world"), "text/plain"),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"
    assert response.json()["attachments"][0]["filename"] == "hello.txt"

    response = client.get(
        "/v1/inboxes/me/messages",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["messages"][0]["attachments_meta"] is not None
    assert "hello.txt" in data["messages"][0]["attachments_meta"]
