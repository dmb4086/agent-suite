import httpx

BASE_URL = "http://localhost:8000"


inbox = httpx.post(f"{BASE_URL}/v1/inboxes").json()
api_key = inbox["api_key"]
print("created", inbox["email_address"])

headers = {"Authorization": f"Bearer {api_key}"}

profile = httpx.get(f"{BASE_URL}/v1/inboxes/me", headers=headers).json()
print("profile", profile)

messages = httpx.get(
    f"{BASE_URL}/v1/inboxes/me/messages",
    headers=headers,
    params={"limit": 10, "unread_only": False},
).json()
print("messages", messages)
