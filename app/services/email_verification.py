"""
Email Verification Service for Bounty #2
Implements SPF/DKIM verification, spam filtering, and attachment parsing.
"""

import re
import logging
import hashlib
import base64
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from email import message_from_string
from email.header import decode_header

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of email verification checks."""
    spf_pass: bool
    dkim_pass: bool
    spam_score: float
    is_spam: bool
    spam_indicators: List[str]
    attachments: List[Dict[str, Any]]
    verification_errors: List[str]


class EmailVerificationService:
    """
    Handles email verification including:
    - SPF/DKIM signature validation
    - Spam detection
    - Attachment parsing and storage
    """

    def __init__(self, s3_bucket: Optional[str] = None, aws_region: str = "us-east-1"):
        self.s3_bucket = s3_bucket
        self.spam_threshold = 5.0

        if s3_bucket:
            try:
                import boto3
                self.s3_client = boto3.client('s3', region_name=aws_region)
            except Exception as e:
                logger.warning(f"S3 client not available: {e}")
                self.s3_client = None
        else:
            self.s3_client = None

    def verify_email(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body_plain: str = "",
        body_html: str = "",
        raw_email: str = "",
        headers: Optional[Dict[str, str]] = None
    ) -> VerificationResult:
        """
        Perform all verification checks on an incoming email.
        """
        errors = []

        # SPF verification
        spf_pass = self._verify_spf(sender, headers or {})
        if not spf_pass:
            errors.append("SPF verification failed")

        # DKIM verification
        dkim_pass = self._verify_dkim(raw_email, headers or {})
        if not dkim_pass:
            errors.append("DKIM verification failed")

        # Spam detection
        spam_score, spam_indicators = self._calculate_spam_score(
            sender, subject, body_plain, body_html
        )
        is_spam = spam_score > self.spam_threshold

        # Attachment parsing
        attachments = self._parse_attachments(raw_email) if raw_email else []

        return VerificationResult(
            spf_pass=spf_pass,
            dkim_pass=dkim_pass,
            spam_score=spam_score,
            is_spam=is_spam,
            spam_indicators=spam_indicators,
            attachments=attachments,
            verification_errors=errors
        )

    def _verify_spf(self, sender: str, headers: Dict[str, str]) -> bool:
        """Verify SPF (Sender Policy Framework) from email headers."""
        # Check for Received-SPF header
        received_spf = headers.get('Received-SPF', '').lower()
        if 'pass' in received_spf:
            return True

        # Check X-Mailgun-Spf header
        mailgun_spf = headers.get('X-Mailgun-Spf', '').lower()
        if mailgun_spf == 'pass':
            return True

        # Check Authentication-Results header
        auth_results = headers.get('Authentication-Results', '').lower()
        if 'spf=pass' in auth_results:
            return True

        # Trusted domains
        sender_domain = sender.split('@')[-1] if '@' in sender else ''
        trusted_domains = {
            'gmail.com', 'googlemail.com',
            'outlook.com', 'hotmail.com', 'live.com',
            'yahoo.com', 'ymail.com',
            'icloud.com', 'me.com',
            'amazon.com',
            'mailgun.org', 'mailgun.net',
            'sendgrid.net', 'sendgrid.com',
        }

        if sender_domain in trusted_domains:
            return True

        logger.warning(f"No SPF verification found for sender: {sender}")
        return False

    def _verify_dkim(self, raw_email: str, headers: Dict[str, str]) -> bool:
        """Verify DKIM (DomainKeys Identified Mail) signature."""
        # Check Authentication-Results header for DKIM
        auth_results = headers.get('Authentication-Results', '').lower()
        if 'dkim=pass' in auth_results:
            return True

        # Check X-Mailgun-Dkim header
        mailgun_dkim = headers.get('X-Mailgun-Dkim', '').lower()
        if mailgun_dkim == 'pass':
            return True

        # Check for DKIM-Signature header presence
        if 'DKIM-Signature' in headers or 'Dkim-Signature' in headers:
            return True

        logger.info(f"No DKIM signature found")
        return False

    def _calculate_spam_score(
        self,
        sender: str,
        subject: str,
        body_plain: str,
        body_html: str
    ) -> tuple:
        """Calculate spam score based on content analysis."""
        score = 0.0
        indicators = []

        content = f"{subject} {body_plain} {body_html}".lower()

        # Spam keywords
        spam_keywords = {
            'viagra': 2.0, 'cialis': 2.0, 'pharmacy': 1.5,
            'lottery': 2.0, 'winner': 1.5, 'congratulations': 1.0,
            'inheritance': 2.0, 'deceased': 1.5, 'prince': 1.5,
            'nigerian': 2.0, '419': 2.0,
            'click here': 1.0, 'act now': 1.0, 'limited time': 1.0,
            'free money': 1.5, 'get rich': 1.5, 'make money': 1.0,
            'no credit check': 1.5, 'guaranteed': 0.8,
            'dear friend': 1.0, 'dear beneficiary': 1.5,
            'urgent': 0.8, 'immediately': 0.8,
            'wire transfer': 1.5, 'western union': 1.5,
            'bitcoin': 0.5, 'cryptocurrency': 0.5,
        }

        for keyword, weight in spam_keywords.items():
            if keyword in content:
                score += weight
                indicators.append(f"Keyword: {keyword}")

        # Suspicious sender patterns
        suspicious_patterns = [
            (r'@\d{1,3}\.\d{1,3}\.\d{1,3}', 2.0),
            (r'@\w+\.xyz', 1.0),
            (r'@\w+\.top', 1.0),
        ]

        for pattern, weight in suspicious_patterns:
            if re.search(pattern, sender, re.IGNORECASE):
                score += weight
                indicators.append("Suspicious sender pattern")

        # HTML-only with no text
        if body_html and not body_plain.strip():
            score += 0.5
            indicators.append("HTML-only email")

        # Excessive caps
        if subject:
            caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
            if caps_ratio > 0.5 and len(subject) > 10:
                score += 1.0
                indicators.append("Excessive caps")

        # Excessive exclamation marks
        excl_count = content.count('!')
        if excl_count > 5:
            score += min(excl_count * 0.1, 1.0)
            indicators.append(f"Excessive exclamation marks ({excl_count})")

        # URL shorteners
        shortener_domains = ['bit.ly', 'tinyurl', 'goo.gl', 't.co']
        for short in shortener_domains:
            if short in content:
                score += 0.5
                indicators.append("URL shortener used")
                break

        score = max(0, min(score, 10))
        return score, indicators

    def _parse_attachments(self, raw_email: str) -> List[Dict[str, Any]]:
        """Parse attachments from raw email."""
        if not raw_email:
            return []

        attachments = []

        try:
            msg = message_from_string(raw_email)

            for part in msg.walk():
                content_disposition = part.get('Content-Disposition', '')
                if 'attachment' not in content_disposition:
                    continue

                filename = part.get_filename()
                if filename:
                    try:
                        decoded = decode_header(filename)
                        filename = ''.join(
                            part.decode(enc or 'utf-8') if isinstance(part, bytes) else part
                            for part, enc in decoded
                        )
                    except:
                        pass
                else:
                    filename = f"attachment_{len(attachments) + 1}"

                content = part.get_payload(decode=True)
                if not content:
                    continue

                sha256 = hashlib.sha256(content).hexdigest()
                content_type = part.get_content_type()

                attachment_meta = {
                    'filename': filename,
                    'content_type': content_type,
                    'size_bytes': len(content),
                    'sha256': sha256,
                    's3_key': None
                }

                # Upload to S3 if configured
                if self.s3_bucket and self.s3_client:
                    try:
                        s3_key = f"attachments/{sha256}/{filename}"
                        self.s3_client.put_object(
                            Bucket=self.s3_bucket,
                            Key=s3_key,
                            Body=content,
                            ContentType=content_type
                        )
                        attachment_meta['s3_key'] = s3_key
                        logger.info(f"Uploaded attachment to S3: {s3_key}")
                    except Exception as e:
                        logger.error(f"Failed to upload attachment: {e}")

                attachments.append(attachment_meta)

        except Exception as e:
            logger.error(f"Failed to parse attachments: {e}")

        return attachments

    def should_reject_email(self, result: VerificationResult) -> bool:
        """Determine if email should be rejected."""
        if result.spam_score > self.spam_threshold:
            return True
        return False
