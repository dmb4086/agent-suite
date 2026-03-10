"""Email verification service for SPF/DKIM validation and spam scoring."""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Optional

import dkim

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of email verification checks."""
    spf_pass: bool
    dkim_pass: bool
    spam_score: float
    is_verified: bool
    is_spam: bool
    rejection_reason: Optional[str] = None


def verify_spf_from_header(spf_header: str) -> bool:
    """Parse SPF result from Mailgun webhook header.

    Mailgun provides SPF check result in the 'X-Mailgun-Spf' field.
    Valid passing values: 'Pass', 'pass'.

    Args:
        spf_header: The SPF result string from Mailgun.

    Returns:
        True if SPF passed, False otherwise.
    """
    if not spf_header:
        return False
    return spf_header.strip().lower() == "pass"


def verify_dkim_from_header(dkim_header: str) -> bool:
    """Parse DKIM result from Mailgun webhook header.

    Mailgun provides DKIM check result in the 'X-Mailgun-Dkim-Check-Result' field.
    Valid passing values: 'Pass', 'pass'.

    Args:
        dkim_header: The DKIM result string from Mailgun.

    Returns:
        True if DKIM passed, False otherwise.
    """
    if not dkim_header:
        return False
    return dkim_header.strip().lower() == "pass"


def verify_dkim_signature(raw_email: bytes) -> bool:
    """Verify DKIM signature on a raw email message using dkimpy.

    This performs actual cryptographic DKIM verification against DNS records.
    Use this when you have access to the raw MIME message.

    Args:
        raw_email: The raw email message bytes.

    Returns:
        True if DKIM signature is valid, False otherwise.
    """
    try:
        return dkim.verify(raw_email)
    except dkim.DKIMException as e:
        logger.warning("DKIM verification failed: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error during DKIM verification: %s", e)
        return False


def parse_spam_score(spam_score_header: str) -> float:
    """Parse spam score from Mailgun webhook data.

    Mailgun provides a spam score as a string. Lower is better.
    A score of 0.0 means no spam indicators found.

    Args:
        spam_score_header: The spam score string from Mailgun.

    Returns:
        The spam score as a float, or 0.0 if parsing fails.
    """
    if not spam_score_header:
        return 0.0
    try:
        return float(spam_score_header)
    except (ValueError, TypeError):
        logger.warning("Could not parse spam score: %s", spam_score_header)
        return 0.0


def verify_mailgun_webhook_signature(
    signing_key: str,
    timestamp: str,
    token: str,
    signature: str
) -> bool:
    """Verify Mailgun webhook signature for authenticity.

    Mailgun signs each webhook POST with HMAC-SHA256 using the
    Mailgun HTTP webhook signing key. This ensures the webhook
    request actually came from Mailgun.

    Args:
        signing_key: The Mailgun webhook signing key.
        timestamp: The timestamp from the webhook payload.
        token: The token from the webhook payload.
        signature: The signature from the webhook payload.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signing_key or not timestamp or not token or not signature:
        return False

    encoded_key = signing_key.encode("utf-8")
    data = f"{timestamp}{token}".encode("utf-8")
    computed = hmac.new(encoded_key, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def verify_email(
    spf_header: str = "",
    dkim_header: str = "",
    spam_score_header: str = "",
    spam_threshold: float = 5.0,
    raw_email: Optional[bytes] = None,
) -> VerificationResult:
    """Perform comprehensive email verification.

    Checks SPF and DKIM results from Mailgun headers, optionally
    verifies DKIM signature cryptographically if raw email is available,
    and evaluates spam score against the configured threshold.

    Args:
        spf_header: SPF result from Mailgun (e.g., 'Pass', 'Fail').
        dkim_header: DKIM result from Mailgun (e.g., 'Pass', 'Fail').
        spam_score_header: Spam score string from Mailgun.
        spam_threshold: Maximum acceptable spam score.
        raw_email: Optional raw MIME message for cryptographic DKIM check.

    Returns:
        VerificationResult with all check results and overall status.
    """
    spf_pass = verify_spf_from_header(spf_header)
    dkim_pass = verify_dkim_from_header(dkim_header)

    # If raw email is available, also verify DKIM cryptographically
    if raw_email and not dkim_pass:
        dkim_pass = verify_dkim_signature(raw_email)

    spam_score = parse_spam_score(spam_score_header)
    is_spam = spam_score > spam_threshold
    is_verified = spf_pass and dkim_pass and not is_spam

    rejection_reason = None
    if is_spam:
        rejection_reason = f"Spam score {spam_score} exceeds threshold {spam_threshold}"
    elif not spf_pass and not dkim_pass:
        rejection_reason = "Both SPF and DKIM verification failed"

    return VerificationResult(
        spf_pass=spf_pass,
        dkim_pass=dkim_pass,
        spam_score=spam_score,
        is_verified=is_verified,
        is_spam=is_spam,
        rejection_reason=rejection_reason,
    )
