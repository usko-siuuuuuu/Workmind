import httpx

response = httpx.get("http://localhost:8025/api/v1/messages")
data = response.json()

msg = data["messages"][0]
msg_id = msg["ID"]
print(f"ID письма: {msg_id}")

detail = httpx.get(f"http://localhost:8025/api/v1/message/{msg_id}").json()
print(f"Тема: {detail['Subject']}")
print(f"Структура detail: {list(detail.keys())}")