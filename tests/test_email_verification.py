"""
Test cases for Email Verification Service
"""
import pytest
from email_verification import EmailVerificationService


@pytest.fixture
def verification_service():
    return EmailVerificationService(
        s3_bucket='test-bucket',
        spam_threshold=5.0
    )


@pytest.mark.asyncio
async def test_valid_email_passes_all_checks(verification_service):
    """测试有效邮件通过所有检查"""
    email_content = """From: sender@example.com
To: recipient@example.com
Subject: Normal email
Message-ID: <12345@example.com>
Date: Mon, 10 Mar 2026 14:00:00 +0000

This is a normal email body.
"""

    result = await verification_service.verify_email(email_content, '192.168.1.1')

    # 应该至少通过垃圾邮件检查
    assert result['spam_score'] < 5.0
    assert result['is_spam'] is False


@pytest.mark.asyncio
async def test_spam_email_detected(verification_service):
    """测试垃圾邮件检测"""
    email_content = """From: spammer@bad.com
To: victim@example.com
Subject: FREE WINNER CLICK HERE ACT NOW!!!

Congratulations! You've won! Click here http://bad.com http://scam.com
"""

    result = await verification_service.verify_email(email_content, '10.0.0.1')

    # 应该被标记为垃圾邮件
    assert result['spam_score'] > 5.0
    assert result['is_spam'] is True


@pytest.mark.asyncio
async def test_spam_score_calculation(verification_service):
    """测试垃圾邮件分数计算"""
    # 测试关键词检测
    email_with_keywords = "Subject: FREE MONEY CLICK HERE"
    score = verification_service._check_spam_score(email_with_keywords)
    assert score > 0

    # 测试正常邮件
    normal_email = "Subject: Meeting tomorrow\n\nHi, let's meet tomorrow."
    normal_score = verification_service._check_spam_score(normal_email)
    assert normal_score < score


def test_attachment_parsing(verification_service):
    """测试附件解析"""
    email_with_attachment = """From: sender@example.com
To: recipient@example.com
Subject: Email with attachment
Content-Type: multipart/mixed; boundary=boundary123

--boundary123
Content-Type: text/plain

This is the body.

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="document.pdf"

<binary content here>

--boundary123--
"""

    # 注意：实际测试需要 mock S3
    attachments = verification_service._parse_attachments(email_with_attachment)

    # 应该识别出附件（即使上传失败）
    assert isinstance(attachments, list)


@pytest.mark.asyncio
async def test_missing_headers_penalized(verification_service):
    """测试缺少必要头部会增加垃圾邮件分数"""
    email_without_headers = """From: test@example.com
Subject: Test

No Message-ID or Date headers.
"""

    result = await verification_service.verify_email(email_without_headers, '127.0.0.1')

    # 应该因为缺少头部而增加分数
    assert result['spam_score'] >= 3.0  # 1.5 + 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
