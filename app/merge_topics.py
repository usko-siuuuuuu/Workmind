import psycopg2
import ollama
import os
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path="C:/workmind/.env")

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    dbname=os.getenv("POSTGRES_DB")
)
cur = conn.cursor()

# Получаем все темы
cur.execute("SELECT id, title, object_name FROM topics ORDER BY id")
topics = cur.fetchall()

if len(topics) < 2:
    print("Меньше двух тем — слияние не нужно")
    exit()

# Формируем список тем для LLM
topics_str = "\n".join([f"ID {t[0]}: '{t[1]}' (объект: {t[2]})" for t in topics])

prompt = f"""Ты — система анализа деловой переписки строительной компании.

Вот список тем переписки:
{topics_str}

Определи какие темы являются частью одной цепочки согласования/обсуждения.
Темы относятся к одной цепочке если они про один и тот же материал/вопрос/объект,
даже если формулировки разные ("согласование поручней" и "дополнительные материалы по поручням" — одна цепочка).

Верни ТОЛЬКО JSON:
{{
  "groups": [
    {{
      "main_id": ID темы которая остаётся главной,
      "merge_ids": [ID тем которые сливаются в главную],
      "final_title": "итоговое название цепочки"
    }}
  ]
}}

Если все темы разные — верни {{"groups": []}}"""

response = ollama.chat(
    model=os.getenv("OLLAMA_MODEL"),
    messages=[{"role": "user", "content": prompt}],
    options={"temperature": 0.1, "num_ctx": 8192},
    think=False
)

raw = response["message"]["content"]
if "```json" in raw:
    raw = raw.split("```json")[1].split("```")[0].strip()
elif "```" in raw:
    raw = raw.split("```")[1].split("```")[0].strip()

result = json.loads(raw)
print(f"Найдено групп для слияния: {len(result['groups'])}")

for group in result["groups"]:
    main_id = group["main_id"]
    merge_ids = group["merge_ids"]
    final_title = group["final_title"]
    
    if not merge_ids:
        continue
    
    print(f"\nСливаем в тему ID {main_id}: '{final_title}'")
    print(f"  Поглощаем темы: {merge_ids}")
    
    # Переносим письма из поглощаемых тем в главную
    for merge_id in merge_ids:
        cur.execute(
            "UPDATE emails SET topic_id = %s WHERE topic_id = %s",
            (main_id, merge_id)
        )
        print(f"  Письма темы {merge_id} → тема {main_id}")
    
    # Обновляем название главной темы
    cur.execute(
        "UPDATE topics SET title = %s WHERE id = %s",
        (final_title, main_id)
    )
    
    # Удаляем поглощённые темы
    for merge_id in merge_ids:
        cur.execute("DELETE FROM topics WHERE id = %s", (merge_id,))

conn.commit()

# Итог
cur.execute("""
    SELECT t.id, t.title, t.object_name, count(e.id) 
    FROM topics t 
    LEFT JOIN emails e ON e.topic_id = t.id 
    GROUP BY t.id ORDER BY t.id
""")
print("\nИтоговые темы:")
for row in cur.fetchall():
    print(f"  ID {row[0]}: '{row[1]}' (объект: {row[2]}) — {row[3]} писем")

cur.close()
conn.close()