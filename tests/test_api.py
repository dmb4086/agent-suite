import pytest
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
            "body_plain": "Test body",
            "message_id": "test123"
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


# ─── Web UI Tests ─────────────────────────────────────────


def test_inbox_page():
    """GET /inbox returns the SPA HTML page."""
    response = client.get("/inbox")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Agent Suite" in response.text


def test_compose_page():
    """GET /compose returns the SPA HTML page."""
    response = client.get("/compose")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Agent Suite" in response.text


def test_message_detail_page():
    """GET /inbox/{id} returns the SPA HTML page."""
    response = client.get("/inbox/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_static_css():
    """Static CSS file is served correctly."""
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_static_js():
    """Static JS file is served correctly."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_inbox_page_contains_key_elements():
    """Verify the HTML page includes essential UI elements."""
    response = client.get("/inbox")
    html = response.text
    # Navigation links
    assert 'href="/inbox"' in html
    assert 'href="/compose"' in html
    # Settings modal
    assert 'id="modal-overlay"' in html
    assert 'id="api-key-input"' in html
    # App container
    assert 'id="app"' in html
    # Static asset references
    assert "/static/style.css" in html
    assert "/static/app.js" in html
