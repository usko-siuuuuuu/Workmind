import httpx

ports = [8025, 8026, 8027, 8028, 8029]

for port in ports:
    try:
        response = httpx.delete(f"http://localhost:{port}/api/v1/messages")
        print(f"Mailpit :{port} — очищен")
    except Exception as e:
        print(f"Mailpit :{port} — ошибка: {e}")