from email.header import decode_header
import ollama
import psycopg2
import json
from dotenv import load_dotenv
import os
import httpx

load_dotenv(dotenv_path="C:/workmind/.env")

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB")
    )

def decode_str(s):
    if s is None:
        return ""
    decoded, encoding = decode_header(s)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")
    return decoded

def fetch_emails():
    response = httpx.get("http://localhost:8025/api/v1/messages")
    data = response.json()
    emails = []
    for msg in data.get("messages", []):
        msg_id = msg["ID"]
        detail = httpx.get(f"http://localhost:8025/api/v1/message/{msg_id}").json()
        emails.append({
            "message_id": msg_id,
            "sender": detail.get("From", {}).get("Address", ""),
            "recipients": ", ".join([r["Address"] for r in detail.get("To", [])]),
            "subject": detail.get("Subject", ""),
            "body": detail.get("Text", "")
        })
    return emails

def extract_tasks_with_llm(email_data):
    prompt = f"""Ты — система анализа деловой переписки строительной компании.

Проанализируй письмо и извлеки задачи для каждого упомянутого сотрудника.

Письмо:
От: {email_data['sender']}
Кому: {email_data['recipients']}
Тема: {email_data['subject']}
Текст:
{email_data['body']}

Верни ответ ТОЛЬКО в формате JSON, без лишнего текста:
{{
  "tasks": [
    {{
      "employee_email": "email сотрудника",
      "title": "краткое название задачи",
      "description": "подробное описание",
      "priority": "high/medium/low",
      "due_date": "YYYY-MM-DD или null"
    }}
  ],
  "risk_flags": ["описание риска если есть"],
  "summary": "краткое резюме письма"
}}"""

    response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL"),
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1},
        think=False
    )

    raw = response["message"]["content"]
    # Убираем thinking-блок если есть
    if "<think>" in raw:
        raw = raw.split("</think>")[-1].strip()
    # Убираем markdown-обёртку если есть
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    return json.loads(raw)

def save_tasks(email_data, parsed):
    conn = get_db_connection()
    cur = conn.cursor()

    # Сохраняем письмо
    cur.execute("""
        INSERT INTO emails (message_id, sender, recipients, subject, body, processed)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        ON CONFLICT (message_id) DO NOTHING
    """, (
        email_data["message_id"],
        email_data["sender"],
        email_data["recipients"],
        email_data["subject"],
        email_data["body"]
    ))

    # Сохраняем задачи
    for task in parsed.get("tasks", []):
        cur.execute("SELECT id FROM employees WHERE email = %s", (task["employee_email"],))
        row = cur.fetchone()
        if row:
            cur.execute("""
                INSERT INTO tasks (employee_id, title, description, source, priority, due_date)
                VALUES (%s, %s, %s, 'email', %s, %s)
            """, (row[0], task["title"], task["description"], task["priority"], task.get("due_date")))
            print(f"  Задача → {task['employee_email']}: {task['title']}")

    conn.commit()
    cur.close()
    conn.close()

# Запуск
print("Читаем письма из Mailpit...")
emails = fetch_emails()
print(f"Найдено писем: {len(emails)}")

for em in emails:
    print(f"\nОбрабатываем: {em['subject']}")
    print("Отправляем в LLM...")
    parsed = extract_tasks_with_llm(em)
    print(f"Резюме: {parsed.get('summary', '')}")
    if parsed.get("risk_flags"):
        print(f"Риски: {parsed['risk_flags']}")
    save_tasks(em, parsed)

print("\nГотово!")