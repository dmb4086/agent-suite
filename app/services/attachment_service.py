"""Attachment service for parsing email attachments and storing in S3."""

import logging
import uuid
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.models import Attachment

logger = logging.getLogger(__name__)


def generate_s3_key(prefix: str, message_id: str, filename: str) -> str:
    """Generate a unique S3 object key for an attachment.

    Uses a UUID to prevent key collisions even if the same filename
    is uploaded for the same message.

    Args:
        prefix: S3 key prefix (e.g., 'attachments').
        message_id: The message UUID string.
        filename: Original attachment filename.

    Returns:
        The S3 object key string.
    """
    unique = uuid.uuid4().hex[:8]
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"{prefix}/{message_id}/{unique}_{safe_filename}"


def get_s3_client(
    aws_access_key_id: str,
    aws_secret_access_key: str,
    aws_region: str,
):
    """Create and return a boto3 S3 client.

    Args:
        aws_access_key_id: AWS access key ID.
        aws_secret_access_key: AWS secret access key.
        aws_region: AWS region name.

    Returns:
        A boto3 S3 client instance.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )


def upload_to_s3(
    s3_client,
    bucket: str,
    key: str,
    file_data: bytes,
    content_type: str,
) -> bool:
    """Upload file data to S3.

    Args:
        s3_client: boto3 S3 client.
        bucket: S3 bucket name.
        key: S3 object key.
        file_data: Raw file bytes.
        content_type: MIME type of the file.

    Returns:
        True if upload succeeded, False otherwise.
    """
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        return True
    except ClientError as e:
        logger.error("Failed to upload to S3: %s", e)
        return False


async def parse_and_store_attachments(
    files: List[UploadFile],
    message_id: str,
    db: Session,
    s3_client,
    bucket: str,
    s3_prefix: str = "attachments",
) -> List[Attachment]:
    """Parse attachments from webhook files and store in S3.

    For each file:
    1. Read the file content
    2. Upload to S3 with a unique key
    3. Create an Attachment database record

    If S3 is not configured (no bucket), attachment metadata is still
    stored but without S3 references.

    Args:
        files: List of UploadFile objects from the webhook.
        message_id: The UUID of the parent Message.
        db: SQLAlchemy database session.
        s3_client: boto3 S3 client (can be None if S3 not configured).
        bucket: S3 bucket name (empty string if not configured).
        s3_prefix: S3 key prefix for organizing attachments.

    Returns:
        List of created Attachment model instances.
    """
    attachments = []

    for file in files:
        file_data = await file.read()
        file_size = len(file_data)
        filename = file.filename or "unnamed"
        content_type = file.content_type or "application/octet-stream"

        s3_key = None
        s3_bucket = None

        if s3_client and bucket:
            s3_key = generate_s3_key(s3_prefix, message_id, filename)
            uploaded = upload_to_s3(s3_client, bucket, s3_key, file_data, content_type)
            if uploaded:
                s3_bucket = bucket
            else:
                logger.warning(
                    "Failed to upload attachment %s to S3, storing metadata only",
                    filename,
                )
                s3_key = None

        attachment = Attachment(
            message_id=message_id,
            filename=filename,
            content_type=content_type,
            size=file_size,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )
        db.add(attachment)
        attachments.append(attachment)

    return attachments
