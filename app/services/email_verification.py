"""
Email Verification Service
实现 SPF/DKIM 验证、垃圾邮件过滤、附件解析
"""
import logging
from typing import Optional, Dict, List, Any
from email import message_from_string
from email.policy import default
import dkimpy
import boto3
from botocore.exceptions import ClientError
import spf

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """邮件验证服务"""

    def __init__(self, s3_bucket: str, spam_threshold: float = 5.0):
        self.s3_bucket = s3_bucket
        self.spam_threshold = spam_threshold
        self.s3_client = boto3.client('s3')

    async def verify_email(self, email_content: str, client_ip: str) -> Dict[str, Any]:
        """
        验证邮件的完整流程

        Args:
            email_content: 原始邮件内容
            client_ip: 发送方IP地址

        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'spf_pass': False,
            'dkim_pass': False,
            'spam_score': 0.0,
            'is_spam': False,
            'attachments': [],
            'errors': []
        }

        try:
            # 1. SPF 验证
            result['spf_pass'] = self._verify_spf(email_content, client_ip)
            logger.info(f"SPF verification: {'PASS' if result['spf_pass'] else 'FAIL'}")

            # 2. DKIM 验证
            result['dkim_pass'] = self._verify_dkim(email_content)
            logger.info(f"DKIM verification: {'PASS' if result['dkim_pass'] else 'FAIL'}")

            # 3. 垃圾邮件检测
            result['spam_score'] = self._check_spam_score(email_content)
            result['is_spam'] = result['spam_score'] > self.spam_threshold
            logger.info(f"Spam score: {result['spam_score']} (threshold: {self.spam_threshold})")

            # 4. 解析附件
            result['attachments'] = self._parse_attachments(email_content)
            logger.info(f"Found {len(result['attachments'])} attachments")

            # 5. 判断整体有效性
            result['valid'] = (
                result['spf_pass'] and
                result['dkim_pass'] and
                not result['is_spam']
            )

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Email verification failed: {e}")

        return result

    def _verify_spf(self, email_content: str, client_ip: str) -> bool:
        """验证 SPF 记录"""
        try:
            # 解析邮件获取发件人域名
            msg = message_from_string(email_content, policy=default)
            from_header = msg.get('From', '')
            if '<' in from_header:
                domain = from_header.split('@')[1].split('>')[0]
            else:
                domain = from_header.split('@')[1] if '@' in from_header else ''

            # 执行 SPF 检查
            query = spf.query(client_ip, from_header, domain)
            result = query.check()

            return result[0] == 'pass'
        except Exception as e:
            logger.error(f"SPF verification error: {e}")
            return False

    def _verify_dkim(self, email_content: str) -> bool:
        """验证 DKIM 签名"""
        try:
            # 使用 dkimpy 验证
            d = dkimpy.DKIM(email_content.encode())
            return d.verify()
        except Exception as e:
            logger.error(f"DKIM verification error: {e}")
            return False

    def _check_spam_score(self, email_content: str) -> float:
        """
        检测垃圾邮件分数
        简化版本：基于规则评分
        """
        score = 0.0

        # 简单的启发式规则
        msg = message_from_string(email_content, policy=default)
        subject = msg.get('Subject', '').lower()
        body = str(msg.get_body(preferencelist=('plain', 'html')))

        # 规则1：主题中的垃圾邮件关键词
        spam_keywords = ['free', 'winner', 'click here', 'act now', 'limited time']
        for keyword in spam_keywords:
            if keyword in subject:
                score += 1.0

        # 规则2：正文中的链接数量
        link_count = body.count('http://') + body.count('https://')
        score += min(link_count * 0.5, 3.0)  # 最多加3分

        # 规则3：大写字母比例
        if body:
            upper_ratio = sum(1 for c in body if c.isupper()) / len(body)
            if upper_ratio > 0.3:
                score += 2.0

        # 规则4：缺少必要头部
        if not msg.get('Message-ID'):
            score += 1.5
        if not msg.get('Date'):
            score += 1.5

        return score

    def _parse_attachments(self, email_content: str) -> List[Dict[str, str]]:
        """解析邮件附件并上传到 S3"""
        attachments = []

        try:
            msg = message_from_string(email_content, policy=default)

            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                # 提取附件信息
                filename = part.get_filename()
                if filename:
                    content = part.get_payload(decode=True)
                    content_type = part.get_content_type()

                    # 上传到 S3
                    s3_key = f"attachments/{filename}"
                    s3_url = self._upload_to_s3(s3_key, content, content_type)

                    attachments.append({
                        'filename': filename,
                        'content_type': content_type,
                        'size': len(content),
                        's3_url': s3_url
                    })

        except Exception as e:
            logger.error(f"Attachment parsing error: {e}")

        return attachments

    def _upload_to_s3(self, key: str, content: bytes, content_type: str) -> str:
        """上传附件到 S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{key}"
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise


# 使用示例
async def handle_incoming_email(email_content: str, client_ip: str) -> Dict:
    """处理接收到的邮件"""
    service = EmailVerificationService(
        s3_bucket='agentwork-attachments',
        spam_threshold=5.0
    )

    result = await service.verify_email(email_content, client_ip)

    if not result['valid']:
        # 拒绝邮件
        return {
            'accepted': False,
            'reason': result.get('errors', ['Verification failed'])
        }

    return {
        'accepted': True,
        'verification': result
    }
