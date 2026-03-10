import imaplib
import email
import re
import logging

class AtlasEmailVerifier:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        
    def fetch_verification_code(self, sender_filter="noreply"):
        logging.info(f"正在從 {self.user} 抓取驗證碼...")
        try:
            mail = imaplib.IMAP4_SSL(self.host)
            mail.login(self.user, self.password)
            mail.select("inbox")
            status, messages = mail.search(None, f'FROM "{sender_filter}"')
            if status == "OK":
                for num in reversed(messages[0].split()):
                    _, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    body = msg.get_payload(decode=True).decode()
                    # 匹配 4-6 位數字驗證碼
                    match = re.search(r'\b\d{4,6}\b', body)
                    if match:
                        return match.group(0)
            mail.logout()
        except Exception as e:
            logging.error(f"郵件驗證失敗: {e}")
        return None
