from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agentsuite"

    # AWS SES
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    ses_from_email: str = ""

    # AWS S3 (attachments)
    s3_bucket: str = ""
    s3_prefix: str = "attachments"

    # Email Verification
    spam_score_threshold: float = 5.0
    mailgun_signing_key: str = ""
    require_dkim: bool = True
    require_spf: bool = True

    # App
    app_name: str = "Agent Suite"
    debug: bool = False

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
