"""
Tests for email verification service (Bounty #2).
"""

import pytest
from app.services.email_verification import EmailVerificationService


@pytest.fixture
def service():
    """Create a fresh service instance for each test."""
    return EmailVerificationService(s3_bucket=None)


def test_spf_verification(service):
    """Test SPF verification logic."""
    result = service._verify_spf("test@example.com", {"Received-SPF": "pass"})
    assert result is True
    
    result = service._verify_spf("unknown@domain.xyz", {})
    assert result is False
    
    # Test with trusted domain
    result = service._verify_spf("user@gmail.com", {})
    assert result is True


def test_dkim_verification(service):
    """Test DKIM verification logic."""
    result = service._verify_dkim("", {})
    assert result is False
    
    # Test with DKIM header
    headers = {"Authentication-Results": "dkim=pass; spf=pass"}
    result = service._verify_dkim("", headers)
    assert result is True


def test_spam_scoring(service):
    """Test spam score calculation."""
    # Legitimate email
    score, indicators = service._calculate_spam_score(
        "user@company.com",
        "Meeting Tomorrow",
        "Hi, let's discuss the project update.",
        "<p>Please find attached the report.</p>",
    )
    assert score < 3.0
    
    # Spam email
    score, indicators = service._calculate_spam_score(
        "prince@nigeria.ng",
        "URGENT: You won $1,000,000!!!",
        "CONGRATULATIONS!!! You have won the lottery!!!",
        "",
    )
    assert score > 5.0
    assert "Keyword: lottery" in indicators


def test_full_verification(service):
    """Test full email verification flow."""
    result = service.verify_email(
        sender="user@company.com",
        recipient="inbox@agents.dev",
        subject="Project Update",
        body_plain="Please find attached the report.",
        body_html="",
        raw_email=""
    )
    
    assert result.spam_score < 3.0
    assert result.is_spam is False
