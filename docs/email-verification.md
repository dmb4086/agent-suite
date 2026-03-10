# Email Verification Service

自动化邮件验证服务，实现 SPF/DKIM 验证、垃圾邮件过滤和附件解析。

## 功能

✅ **SPF/DKIM 验证**
- 验证发件人域名的 SPF 记录
- 验证 DKIM 签名完整性

✅ **垃圾邮件过滤**
- 基于规则的垃圾邮件评分
- 可配置阈值（默认 5.0）

✅ **附件解析**
- 自动提取邮件附件
- 上传到 S3 存储
- 返回附件元数据

## 安装

```bash
pip install dkimpy boto3 spf
```

## 使用方法

```python
from email_verification import EmailVerificationService

# 初始化服务
service = EmailVerificationService(
    s3_bucket='your-bucket-name',
    spam_threshold=5.0
)

# 验证邮件
result = await service.verify_email(
    email_content='...',
    client_ip='192.168.1.1'
)

if result['valid']:
    print("✅ 邮件验证通过")
else:
    print("❌ 邮件验证失败")
    print(f"原因: {result['errors']}")
```

## API 响应格式

```json
{
  "valid": true,
  "spf_pass": true,
  "dkim_pass": true,
  "spam_score": 2.5,
  "is_spam": false,
  "attachments": [
    {
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size": 102400,
      "s3_url": "https://bucket.s3.amazonaws.com/attachments/document.pdf"
    }
  ],
  "errors": []
}
```

## 测试

```bash
pytest test_email_verification.py -v
```

## 技术栈

- **dkimpy**: DKIM 签名验证
- **spf**: SPF 记录检查
- **boto3**: AWS S3 附件存储

## 注意事项

- 需要 AWS 凭证配置
- 垃圾邮件检测为简化版本，生产环境建议使用 SpamAssassin
- S3 上传需要适当权限

---

🤖 自动化完成 by OpenClaw Bounty Bot
