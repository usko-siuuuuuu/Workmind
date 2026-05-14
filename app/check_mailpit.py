import httpx

for port, name in [(8025, "МонотекСтрой"), (8026, "ИнвестСтрой"), 
                   (8027, "ГПИ Проект"), (8028, "ФасадТех"), (8029, "ИнтерьерСтрой")]:
    r = httpx.get(f"http://localhost:{port}/api/v1/messages")
    total = r.json().get("total", 0)
    print(f"{name}: {total} писем")