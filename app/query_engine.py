import ollama
import psycopg2
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(dotenv_path="C:/workmind/.env")

# Выбор модели
models = {
    "1": "qwen3.5:4b-q4_K_M",
    "2": "huihui_ai/qwen3.5-abliterated:9b-Qwopus-q4_K",
    "3": "huihui_ai/qwen3-abliterated:14b-q4_K_M"
}
print("Выберите модель для поиска:")
print("  1. Qwen3.5 4B (быстрая)")
print("  2. Qwen3.5 9B (оптимальная)")
print("  3. Qwen3 14B (мощная)")
choice = input("Введите номер [2]: ").strip() or "2"
model = models.get(choice, models["2"])
os.environ["OLLAMA_MODEL"] = model
print(f"Используется модель: {model}\n")

def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB")
    )

def get_neo4j():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

def search_context(question, driver, conn):
    """Ищет релевантный контекст в графе и БД по вопросу"""
    cur = conn.cursor()
    context = []

    # 1. Определяем о чём вопрос — LLM извлекает ключевые слова
    keywords_response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL"),
        messages=[{"role": "user", "content": f"""Извлеки из вопроса ключевые слова для поиска.
Вопрос: {question}

Верни ТОЛЬКО JSON:
{{"keywords": ["слово1", "слово2"], "object": "номер объекта или null", "person": "имя или email или null"}}"""}],
        options={"temperature": 0, "num_ctx": 4096},
        think=False
    )
    raw = keywords_response["message"]["content"]
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    
    try:
        search_params = json.loads(raw)
    except:
        search_params = {"keywords": [question], "object": None, "person": None}

    keywords = search_params.get("keywords", [])
    obj = search_params.get("object")
    person = search_params.get("person")

    # 2. LLM сама выбирает релевантные темы
    cur.execute("SELECT id, title, object_name FROM topics")
    topics = cur.fetchall()
    
    if topics:
        topics_str = "\n".join([f"ID {t[0]}: '{t[1]}' (объект: {t[2]})" for t in topics])
        
        topic_response = ollama.chat(
            model=os.getenv("OLLAMA_MODEL"),
            messages=[{"role": "user", "content": f"""Определи какие темы из списка релевантны для ответа на вопрос.

Вопрос: {question}

Темы:
{topics_str}

Верни ТОЛЬКО JSON:
{{"relevant_ids": [1, 2]}}

Если ни одна не подходит — верни {{"relevant_ids": []}}"""}],
            options={"temperature": 0, "num_ctx": 4096},
            think=False
        )
        
        raw = topic_response["message"]["content"]
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        
        try:
            topic_result = json.loads(raw)
            relevant_topic_ids = topic_result.get("relevant_ids", [])
        except:
            relevant_topic_ids = []
        
        relevant_topics = [(t[0], t[1], t[2], 1) for t in topics if t[0] in relevant_topic_ids]
    else:
        relevant_topics = []

    # 3. По найденным темам берём письма
    for topic_id, title, object_name, _ in relevant_topics[:2]:
        cur.execute("""
            SELECT e.subject, e.sender, e.recipients, e.body,
                   e.email_type, e.outgoing_number, e.reply_to_number,
                   e.received_at, e.attachments_text
            FROM emails e
            WHERE e.topic_id = %s
            ORDER BY e.received_at
        """, (topic_id,))
        emails = cur.fetchall()
        
        context.append(f"\n=== ТЕМА: {title} (Объект: {object_name}) ===")
        for em in emails:
            context.append(f"""
Письмо: {em[0]}
От: {em[1]} → Кому: {em[2]}
Тип: {em[4]} | Исх.№: {em[5]} | На №: {em[6]}
Текст: {em[3][:500]}
{f"Вложения: {em[8][:500]}" if em[8] else ""}
---""")

    # 4. Если вопрос про человека — ищем его участие
    if person:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                WHERE p.name CONTAINS $name OR p.email CONTAINS $name
                MATCH (p)-[:ОТПРАВИЛ|ПОЛУЧИЛ]-(e:Email)-[:ОТНОСИТСЯ_К]->(t:Topic)
                RETURN p.name, p.email, e.subject, t.title
                LIMIT 10
            """, name=person)
            rows = result.data()
            if rows:
                context.append(f"\n=== УЧАСТИЕ {person} В ПЕРЕПИСКЕ ===")
                for row in rows:
                    context.append(f"  {row['e.subject']} → тема: {row['t.title']}")

    # 5. Статистика из графа
    with driver.session() as session:
        for topic_id, title, object_name, _ in relevant_topics[:2]:
            result = session.run("""
                MATCH (t:Topic {db_id: $id})
                MATCH (e:Email)-[:ОТНОСИТСЯ_К]->(t)
                MATCH (p:Person)-[:ОТПРАВИЛ]->(e)
                RETURN collect(DISTINCT p.name) as senders,
                       count(e) as email_count
            """, id=topic_id)
            row = result.single()
            if row:
                context.append(f"\nУчастники темы '{title}': {row['senders']}")
                context.append(f"Всего писем в цепочке: {row['email_count']}")

    cur.close()
    return "\n".join(context)

def answer_question(question):
    driver = get_neo4j()
    conn = get_db()

    print(f"\nВопрос: {question}")
    print("Ищу контекст в базе знаний...")
    
    context = search_context(question, driver, conn)
    
    if not context.strip():
        print("Прямой контекст не найден — анализирую всю переписку...")
        cur = conn.cursor()
        cur.execute("""
            SELECT e.subject, e.sender, e.recipients, e.body, t.title,
                   e.attachments_text
            FROM emails e
            LEFT JOIN topics t ON e.topic_id = t.id
            ORDER BY e.received_at
        """)
        all_emails = cur.fetchall()
        cur.close()
        
        context = "=== ВСЯ ПЕРЕПИСКА В СИСТЕМЕ ===\n"
        for em in all_emails:
            context += f"""
Тема письма: {em[0]}
От: {em[1]} → Кому: {em[2]}
Цепочка: {em[4]}
Текст: {em[3][:300]}
{f"Вложения: {em[5][:300]}" if em[5] else ""}
---"""

    prompt = f"""Ты — корпоративный ИИ-ассистент строительной компании МонотекСтрой.
Отвечай на вопросы сотрудников на основе данных из корпоративной переписки.

ДАННЫЕ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ВОПРОС СОТРУДНИКА: {question}

Правила ответа:
- Отвечай только на основе предоставленных данных
- Если данных недостаточно — так и скажи
- Указывай конкретные письма, даты, исходящие номера если они есть
- Отвечай по-русски, кратко и по делу
- Если есть риски или открытые вопросы — упомяни их"""

    response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL"),
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2, "num_ctx": 24576},
        think=False
    )

    answer = response["message"]["content"]
    print(f"\nОтвет:\n{answer}")
    
    driver.close()
    conn.close()
    return answer

# Интерактивный режим
print("=== Корпоративный ИИ-ассистент WorkMind ===")
print("Задавайте вопросы по корпоративной переписке.")
print("Введите 'выход' для завершения.\n")

while True:
    question = input("Ваш вопрос: ").strip()
    if question.lower() in ["выход", "exit", "quit"]:
        print("До свидания!")
        break
    if not question:
        continue
    answer_question(question)
    print()