import httpx
import ollama
import psycopg2
import json
import time
from attachment_processor import extract_text_from_attachment
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(dotenv_path="C:/workmind/.env")
print(f"Используемая модель: {os.getenv('OLLAMA_MODEL')}")

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

def fetch_emails(port=8025):
    response = httpx.get(f"http://localhost:{port}/api/v1/messages")
    data = response.json()
    emails = []
    for msg in data.get("messages", []):
        msg_id = msg["ID"]
        detail = httpx.get(f"http://localhost:{port}/api/v1/message/{msg_id}").json()
        to_list = [r["Address"] for r in detail.get("To", [])]
        cc_list = [r["Address"] for r in detail.get("Cc", [])]
        # Скачиваем вложения
        attachments_text = []
        for att in detail.get("Attachments", []):
            att_id = att.get("PartID")
            filename = att.get("FileName", "")
            if att_id and filename:
                ext = os.path.splitext(filename)[1].lower()
                if ext in [".pdf", ".docx", ".doc", ".txt"]:
                    save_path = os.path.join(
                        r"C:\workmind\storage\attachments",
                        f"{msg_id}_{filename}"
                    )
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file_resp = httpx.get(
                        f"http://localhost:{port}/api/v1/message/{msg_id}/part/{att_id}"
                    )
                    with open(save_path, "wb") as f:
                        f.write(file_resp.content)
                    text = extract_text_from_attachment(save_path)
                    if text.strip():
                        attachments_text.append(f"[Вложение: {filename}]\n{text[:2000]}")

        emails.append({
            "message_id": msg_id,
            "sender": detail.get("From", {}).get("Address", ""),
            "sender_name": detail.get("From", {}).get("Name", ""),
            "recipients": to_list,
            "cc": cc_list,
            "subject": detail.get("Subject", ""),
            "body": detail.get("Text", ""),
            "date": detail.get("Date", ""),
            "attachments_text": "\n\n".join(attachments_text)
        })
    # Сортируем по дате — от старых к новым
    emails.sort(key=lambda x: x["date"])
    return emails

def get_person_name(email, cur):
    # Ищем имя в наших сотрудниках
    cur.execute("SELECT name FROM employees WHERE email = %s", (email,))
    row = cur.fetchone()
    if row:
        return row[0]
    # Ищем во внешних контактах
    cur.execute("SELECT name FROM external_contacts WHERE email = %s", (email,))
    row = cur.fetchone()
    if row:
        return row[0]
    return email

def get_org_by_email(email):
    domain = email.split("@")[-1] if "@" in email else ""
    return domain

def analyze_email(email_data, existing_topics, cur):
    # Обогащаем имя отправителя из БД если не пришло
    sender_name = email_data.get("sender_name", "")
    if not sender_name or sender_name == email_data["sender"]:
        sender_name = get_person_name(email_data["sender"], cur)

    topics_str = "\n".join([
        f"- ID {t[0]}: '{t[1]}' (объект: {t[2]})"
        for t in existing_topics
    ]) if existing_topics else "Нет существующих тем"

    # Добавляем текст вложений если есть
    attachments_context = ""
    if email_data.get("attachments_text"):
        attachments_context = f"\n\nСОДЕРЖИМОЕ ВЛОЖЕНИЙ:\n{email_data['attachments_text'][:3000]}"

    prompt = f"""Ты — система анализа деловой переписки строительной компании МонотекСтрой.

Проанализируй письмо и извлеки структурированную информацию.

ПИСЬМО:
От: {sender_name} <{email_data['sender']}>
Кому: {', '.join(email_data['recipients'])}
Копия: {', '.join(email_data['cc'])}
Тема: {email_data['subject']}
Дата: {email_data['date']}
Текст:
{email_data['body'][:2000]}{attachments_context}

СУЩЕСТВУЮЩИЕ ТЕМЫ В СИСТЕМЕ:
{topics_str}

ПРАВИЛА — ВЫПОЛНЯЙ СТРОГО И БУКВАЛЬНО, БЕЗ ИСКЛЮЧЕНИЙ:

1. ГЛАВНОЕ ПРАВИЛО — ПОИСК СУЩЕСТВУЮЩЕЙ ТЕМЫ:
   Перед созданием новой темы ОБЯЗАТЕЛЬНО проверь каждую существующую тему.
   Новую тему создаёшь ТОЛЬКО если ни одна существующая тема не подходит.
   Если подходящая тема найдена — используй её existing_topic_id. Точка.

2. ЧТО ТАКОЕ ОДНА ТЕМА:
   Одна тема = один непрерывный процесс вокруг одного документа или вопроса 
   на одном объекте. Все письма которые двигают вперёд один и тот же вопрос 
   или документ — это одна тема. Не важно сколько людей участвует и сколько 
   времени прошло между письмами.
   ПРИМЕРЫ ОДНОЙ ТЕМЫ: запрос документа + получение документа = одна тема.
   Замечания к акту + исправление акта + подписание акта = одна тема.
   Предписание + план устранения + отчёт об устранении + снятие замечаний = одна тема.
   ПРИМЕРЫ РАЗНЫХ ТЕМ: договор субподряда и акт КС-2 по нему = разные темы.
   Проектная документация и исполнительная документация = разные темы всегда.
   Геодезия и исполнительная документация = разные темы всегда.

3. КОГДА СОЗДАВАТЬ НОВУЮ ТЕМУ:
   Только если письмо начинает принципиально новый тип процесса которого 
   ещё нет ни в одной существующей теме. Во всех остальных случаях — 
   используй существующую тему.

4. ОДИН ОБЪЕКТ — НЕСКОЛЬКО ТЕМ:
   На одном объекте ОБЯЗАТЕЛЬНО создавай отдельную тему для каждого 
   отдельного процесса. Никогда не объединяй разные процессы в одну тему 
   только потому что объект один. Примеры процессов которые всегда разные 
   темы даже на одном объекте: договор субподряда, акт КС-2, замечания 
   и предписания, исполнительная документация, проектная документация, 
   геодезия и контроль конструкций, протокол совещания.

5. ОБЪЕКТ НЕ УКАЗАН В ПИСЬМЕ — ЖЁСТКИЙ АЛГОРИТМ БЕЗ ИСКЛЮЧЕНИЙ:
   Создавать тему с object_name = null ЗАПРЕЩЕНО если в системе есть 
   хотя бы одна существующая тема. Выполни все четыре шага:
   
   ШАГ 1 — АНАЛИЗ ТЕКСТА: найди в тексте письма любые конкретные слова — 
   названия работ, материалов, документов, конструкций, номера актов, 
   договоров, этажей, помещений, имена людей, организаций.
   
   ШАГ 2 — ПОИСК ПО СОДЕРЖАНИЮ: найди существующую тему где встречаются 
   те же слова или описывается тот же процесс что найден в шаге 1.
   
   ШАГ 3 — ПОИСК ПО УЧАСТНИКАМ: если шаг 2 не дал результата — найди 
   существующую тему где отправитель или получатели этого письма уже 
   участвовали в переписке раньше.
   
   ШАГ 4 — ВЫБОР ТЕМЫ: если шаг 2 или шаг 3 дал совпадение — немедленно 
   используй найденную тему. Установи existing_topic_id равным ID этой темы. 
   Возьми object_name из этой темы и используй его в своём ответе.
   Только если оба шага 2 и 3 не дали ни одного совпадения — создай 
   новую тему с object_name = null.

6. НОМЕРА ПИСЕМ — ОБЯЗАТЕЛЬНО:
   Всегда извлекай outgoing_number из текста в формате "Исх. №XXX".
   Всегда извлекай reply_to_number из текста в формате "На №XXX".
   Если номера есть в тексте но ты их не указал — это ошибка.

7. НАЗВАНИЕ ТЕМЫ — КОНКРЕТНО И ИНФОРМАТИВНО:
   Название темы ОБЯЗАНО содержать конкретный предмет И название объекта.
   Правильно: "Акт КС-2 Этап 1 монтажа фасада — ТЦ Галактика".
   Правильно: "Исполнительная документация по монолитным конструкциям — Апарт-отель Аврора".
   Правильно: "Устранение замечаний по отделке — МЦ Здоровье".
   ЗАПРЕЩЕНО: "Фасад — ТЦ Галактика", "Работы — МЦ Здоровье", "Документы — Аврора".
   Название должно однозначно описывать о чём переписка без чтения писем.

8. РАЗНЫЕ ПРОЦЕССЫ — РАЗНЫЕ ТЕМЫ ВСЕГДА БЕЗ ИСКЛЮЧЕНИЙ:
   Следующие процессы НИКОГДА не объединяются в одну тему ни при каких условиях:
   — проектная документация (РД, разъяснения, изменения проекта)
   — исполнительная документация (ИД, АОСР, исполнительные схемы)
   — геодезия и контроль конструкций
   — акты КС-2 и приёмка работ
   — договоры субподряда
   — замечания и предписания заказчика
   — протоколы совещаний
   Каждый из этих процессов — отдельная тема даже если объект один и тот же.

Верни ТОЛЬКО JSON:
{{
  "email_type": "первичное/ответ/пересылка/уточнение",
  "topic_title": "краткое название темы",
  "object_name": "название объекта или null",
  "existing_topic_id": null или ID существующей темы,
  "outgoing_number": "исходящий номер или null",
  "reply_to_number": "номер письма на которое отвечает или null",
  "is_forward": true или false,
  "summary": "одно предложение о чём письмо",
  "risk_flags": [] или ["описание риска"]
}}"""

    response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL"),
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1, "num_ctx": 16384},
        think=False
    )

    raw = response["message"]["content"]
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    # Очищаем управляющие символы которые ломают JSON
    raw = ''.join(ch for ch in raw if ord(ch) >= 32 or ch in '\n\r\t')
    try:
        return json.loads(raw), sender_name
    except json.JSONDecodeError:
        # Пробуем найти JSON в тексте
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group()), sender_name
            except:
                pass
        # Возвращаем заглушку если совсем не получилось
        print(f"  ОШИБКА парсинга JSON, пропускаем письмо")
        return {
            "email_type": "первичное",
            "topic_title": email_data["subject"][:100],
            "object_name": None,
            "existing_topic_id": None,
            "outgoing_number": None,
            "reply_to_number": None,
            "is_forward": False,
            "summary": "Не удалось распознать",
            "risk_flags": []
        }, sender_name

def find_or_create_topic(cur, analysis):
    existing_id = analysis.get("existing_topic_id")
    if existing_id:
        cur.execute("SELECT id FROM topics WHERE id = %s", (existing_id,))
        if cur.fetchone():
            # Обновляем объект если он появился
            if analysis.get("object_name"):
                cur.execute("""
                    UPDATE topics SET object_name = %s 
                    WHERE id = %s AND object_name IS NULL
                """, (analysis["object_name"], existing_id))
            return existing_id

    cur.execute("""
        INSERT INTO topics (title, object_name)
        VALUES (%s, %s) RETURNING id
    """, (analysis["topic_title"], analysis.get("object_name")))
    return cur.fetchone()[0]

def save_email(cur, email_data, analysis, topic_id):
    cur.execute("""
        INSERT INTO emails
            (message_id, sender, recipients, subject, body,
            email_type, outgoing_number, reply_to_number, topic_id, 
            processed, attachments_text)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s)
        ON CONFLICT (message_id) DO UPDATE
            SET topic_id = EXCLUDED.topic_id,
                email_type = EXCLUDED.email_type,
                outgoing_number = EXCLUDED.outgoing_number,
                reply_to_number = EXCLUDED.reply_to_number,
                attachments_text = EXCLUDED.attachments_text,
                processed = TRUE
        RETURNING id
    """, (
        email_data["message_id"],
        email_data["sender"],
        ", ".join(email_data["recipients"] + email_data["cc"]),
        email_data["subject"],
        email_data["body"],
        analysis["email_type"],
        analysis.get("outgoing_number"),
        analysis.get("reply_to_number"),
        topic_id,
        email_data.get("attachments_text", "")
    ))
    return cur.fetchone()[0]

def update_graph(driver, email_data, analysis, topic_id, email_db_id, sender_name, cur):
    with driver.session() as session:

        # Узел письма
        session.run("""
            MERGE (e:Email {message_id: $message_id})
            SET e.subject = $subject,
                e.date = $date,
                e.type = $email_type,
                e.summary = $summary,
                e.outgoing_number = $out_num,
                e.reply_to_number = $reply_num,
                e.db_id = $db_id
        """, message_id=email_data["message_id"],
             subject=email_data["subject"],
             date=email_data["date"],
             email_type=analysis["email_type"],
             summary=analysis["summary"],
             out_num=analysis.get("outgoing_number", ""),
             reply_num=analysis.get("reply_to_number", ""),
             db_id=email_db_id)

        # Тема
        session.run("""
            MERGE (t:Topic {db_id: $topic_id})
            SET t.title = $title,
                t.object_name = $object_name
            WITH t
            MATCH (e:Email {message_id: $message_id})
            MERGE (e)-[:ОТНОСИТСЯ_К]->(t)
        """, topic_id=topic_id,
             title=analysis["topic_title"],
             object_name=analysis.get("object_name") or "",
             message_id=email_data["message_id"])

        # Отправитель — находим существующий узел или создаём если неизвестный
        sender_domain = get_org_by_email(email_data["sender"])
        session.run("""
            MERGE (s:Person {email: $email})
            SET s.name = CASE WHEN s.name IS NULL THEN $name ELSE s.name END
            WITH s
            MATCH (em:Email {message_id: $message_id})
            MERGE (s)-[:ОТПРАВИЛ]->(em)
            WITH s
            OPTIONAL MATCH (o:Organization {domain: $domain})
            FOREACH (org IN CASE WHEN o IS NOT NULL THEN [o] ELSE [] END |
                MERGE (s)-[:WORKS_AT]->(org)
            )
        """, email=email_data["sender"],
             name=sender_name,
             message_id=email_data["message_id"],
             domain=sender_domain)

        # Получатели
        for recipient in email_data["recipients"] + email_data["cc"]:
            r_name = get_person_name(recipient, cur)
            r_domain = get_org_by_email(recipient)
            session.run("""
                MERGE (r:Person {email: $email})
                SET r.name = CASE WHEN r.name IS NULL THEN $name ELSE r.name END
                WITH r
                MATCH (em:Email {message_id: $message_id})
                MERGE (em)-[:ПОЛУЧИЛ]->(r)
                WITH r
                OPTIONAL MATCH (o:Organization {domain: $domain})
                FOREACH (org IN CASE WHEN o IS NOT NULL THEN [o] ELSE [] END |
                    MERGE (r)-[:WORKS_AT]->(org)
                )
            """, email=recipient,
                 name=r_name,
                 message_id=email_data["message_id"],
                 domain=r_domain)

        # Связь с предыдущим письмом по reply_to_number
        if analysis.get("reply_to_number"):
            session.run("""
                MATCH (em:Email {message_id: $message_id})
                MATCH (prev:Email {outgoing_number: $reply_num})
                MERGE (em)-[:ЯВЛЯЕТСЯ_ОТВЕТОМ_НА]->(prev)
            """, message_id=email_data["message_id"],
                 reply_num=analysis["reply_to_number"])

def auto_merge_topics(conn, driver):
    """Автоматически сливает похожие темы после обработки"""
    cur = conn.cursor()
    cur.execute("SELECT id, title, object_name FROM topics ORDER BY id")
    topics = cur.fetchall()

    if len(topics) < 2:
        return

    cur.execute("""
        SELECT t.id, t.title, t.object_name, count(e.id) as cnt,
               string_agg(DISTINCT e.sender, ', ') as senders
        FROM topics t 
        LEFT JOIN emails e ON e.topic_id = t.id 
        GROUP BY t.id 
        ORDER BY t.id
    """)
    topics_with_details = cur.fetchall()

    topics_str = "\n".join([
        f"ID {t[0]}: '{t[1]}' | объект: '{t[2]}' | писем: {t[3]} | участники: {t[4]}"
        for t in topics_with_details
    ])

    prompt = f"""Ты — строгий классификатор тем деловой переписки строительной компании.

КРИТИЧЕСКОЕ ПРАВИЛО — ПРОВЕРЯЙ ОБЪЕКТ ПЕРЕД СЛИЯНИЕМ:
Сравни поле "объект" обеих тем.
Если объекты разные — ЗАПРЕЩЕНО сливать абсолютно.
Если объект одной темы None — НЕ сливать с темой где объект указан.
Это правило имеет приоритет над всеми остальными.

═══════════════════════════════════════════

ВХОДНЫЕ ДАННЫЕ — список тем:
{topics_str}

ЗАДАЧА: определить темы которые ИДЕНТИЧНЫ по смыслу и должны быть слиты в одну.

═══════════════════════════════════════════
КРИТЕРИИ СЛИЯНИЯ — все три должны выполняться ОДНОВРЕМЕННО:
1. ОДИН И ТОТ ЖЕ объект строительства
2. ОДИН И ТОТ ЖЕ материал, конструкция или вопрос
3. ОДНА И ТА ЖЕ цепочка согласования/обсуждения

═══════════════════════════════════════════
АБСОЛЮТНЫЕ ЗАПРЕТЫ:

[ОБЪЕКТ]
- Любые разные номера, названия или адреса объектов = разные темы ВСЕГДА
- Если объект одной темы не указан а у другой указан = НЕ сливать
- Разные секции, очереди, корпуса одного объекта = разные темы

[КОНСТРУКТИВНЫЕ ЭЛЕМЕНТЫ И МАТЕРИАЛЫ]
Каждый из перечисленных элементов является ОТДЕЛЬНОЙ темой и не может быть слит с другим:
— несущие конструкции: фундамент, сваи, ростверк, колонны, балки, перекрытия, стены, диафрагмы жёсткости
— ограждающие конструкции: фасад, витраж, кровля, кровельный пирог, парапет, водосток
— внутренние конструкции: перегородки, полы, потолки, лестницы, пандусы, поручни
— инженерные системы: вентиляция, кондиционирование, отопление, водоснабжение, канализация, электроснабжение, слаботочные системы, лифты, эскалаторы
— фасадные системы: навесной фасад, штукатурный фасад, панели, облицовка, утеплитель
— кровельные системы: мембрана, утеплитель кровли, стяжка, примыкания
— окна и двери: оконные блоки, дверные блоки, витражи, противопожарные двери
— благоустройство: асфальт, тротуарная плитка, озеленение, ограждения, МАФ
— материалы: бетон, арматура, кирпич, металлоконструкции, сэндвич-панели, профлист
— прочее: геодезия, исполнительная документация, акты, сметы

[ПРОЦЕССЫ]
Разные процессы в рамках одного элемента = разные темы если нет явной цепочки:
— согласование ≠ претензия ≠ поставка ≠ замена ≠ гарантия ≠ приёмка
— исключение: если претензия явно является следствием согласования того же элемента
  на том же объекте — это одна цепочка

[КОНТРАГЕНТЫ]
- Разные субподрядчики по разным вопросам = разные темы
- Переписка с проектировщиком ≠ переписка с заказчиком по тому же вопросу
  только если это разные независимые цепочки

═══════════════════════════════════════════
РАЗРЕШЕНО СЛИВАТЬ — только если:
- Одинаковый объект + одинаковый конкретный предмет + явная цепочка
- "Акт КС-2 Этап 1" + "Акт КС-2 Этап 1 исправленный" = одна цепочка ✓
- "Замечания по предписанию" + "Устранение замечаний по предписанию" = одна цепочка ✓
- "Запрос разъяснений к РД" + "Ответ на запрос разъяснений к РД" = одна цепочка ✓
- Тема с object=None + тема с объектом = сливать ТОЛЬКО если содержание явно про тот же объект

ЗАПРЕЩЕНО СЛИВАТЬ:
- Договор субподряда + Акты КС-2 — разные документы даже по одному объекту
- Замечания по отделке + Замечания по фасаду — разные виды работ
- Всё что на разных объектах
- Темы с object=None если объект неочевиден из названия
- РД (проектная документация) ≠ ИД (исполнительная документация) — никогда не сливать
- Геодезия/отклонения конструкций ≠ ИД ≠ РД
- Договор субподряда ≠ замечания/акты по этому же субподряду

═══════════════════════════════════════════
ПРАВИЛА СЛИЯНИЯ:
- keep_id = тема с НАИМЕНЬШИМ ID
- final_title = конкретный предмет + объект. 
  Формат: "[Конкретный вид работ/документ] — [Объект]"
  Примеры: "Монтаж НВФ — ТЦ Галактика", "Устранение замечаний по отделке — МЦ Здоровье"
  НЕ использовать просто "Фасад — Объект" или "Работы — Объект"

═══════════════════════════════════════════
ФОРМАТ ОТВЕТА — ТОЛЬКО JSON, никакого текста вокруг:
{{
  "merges": [
    {{
      "keep_id": числовой ID темы которая остаётся,
      "absorb_ids": [числовые ID тем которые поглощаются],
      "final_title": "итоговое название темы"
    }}
  ]
}}

Если ни одна пара тем не соответствует критериям слияния — верни:
{{"merges": []}}"""

    response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL"),
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1, "num_ctx": 16384},
        think=False
    )

    raw = response["message"]["content"]
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    result = json.loads(raw)

    deleted_ids = set()

    for merge in result.get("merges", []):
        keep_id = merge["keep_id"]
        absorb_ids = merge["absorb_ids"]
        final_title = merge["final_title"]

        if keep_id in deleted_ids:
            continue

        for absorb_id in absorb_ids:
            if absorb_id in deleted_ids:
                continue
            deleted_ids.add(absorb_id)

        for absorb_id in absorb_ids:
            # СНАЧАЛА переназначаем письма
            cur.execute(
                "UPDATE emails SET topic_id = %s WHERE topic_id = %s",
                (keep_id, absorb_id)
            )
            conn.commit()  # коммитим переназначение ДО удаления темы
            
            # ПОТОМ обновляем граф
            with driver.session() as session:
                session.run("""
                    MATCH (t1:Topic {db_id: $keep_id})
                    MATCH (t2:Topic {db_id: $absorb_id})
                    MATCH (e:Email)-[r:ОТНОСИТСЯ_К]->(t2)
                    MERGE (e)-[:ОТНОСИТСЯ_К]->(t1)
                    DELETE r
                """, keep_id=keep_id, absorb_id=absorb_id)
                session.run(
                    "MATCH (t:Topic {db_id: $id}) DETACH DELETE t",
                    id=absorb_id
                )
            # ПОТОМ удаляем тему
            cur.execute("DELETE FROM topics WHERE id = %s", (absorb_id,))
            conn.commit()

        cur.execute(
            "UPDATE topics SET title = %s WHERE id = %s",
            (final_title, keep_id)
        )
        with driver.session() as session:
            session.run(
                "MATCH (t:Topic {db_id: $id}) SET t.title = $title",
                id=keep_id, title=final_title
            )

        print(f"  Слито в '{final_title}': поглощены {absorb_ids}")

    conn.commit()
    cur.close()

def process_all():
    # Выбор модели
    models = {
        "1": "qwen3.5:4b-q4_K_M",
        "2": "huihui_ai/qwen3.5-abliterated:9b-Qwopus-q4_K",
        "3": "huihui_ai/qwen3-abliterated:14b-q4_K_M"
    }
    print("Выберите модель:")
    print("  1. Qwen3.5 4B (быстрая)")
    print("  2. Qwen3.5 9B (оптимальная)")
    print("  3. Qwen3 14B (мощная)")
    choice = input("Введите номер [2]: ").strip() or "2"
    model = models.get(choice, models["2"])
    os.environ["OLLAMA_MODEL"] = model
    print(f"Используется модель: {model}\n")

    conn = get_db()
    cur = conn.cursor()
    driver = get_neo4j()

    cur.execute("SELECT id, title, object_name FROM topics ORDER BY id")
    existing_topics = cur.fetchall()

    print("Читаем письма МонотекСтрой...")
    emails = fetch_emails(port=8025)
    new_emails = [e for e in emails if not check_processed(cur, e["message_id"])]
    print(f"Всего писем: {len(emails)}, новых: {len(new_emails)}")

    for em in new_emails:
        print(f"\n{'='*50}")
        print(f"Обрабатываем: {em['subject']}")
        print(f"От: {em['sender']} | Дата: {em['date']}")

        analysis, sender_name = analyze_email(em, existing_topics, cur)

        print(f"Тип: {analysis['email_type']}")
        print(f"Тема: {analysis['topic_title']}")
        print(f"Объект: {analysis.get('object_name', '—')}")
        print(f"Исх.№: {analysis.get('outgoing_number', '—')} | На №: {analysis.get('reply_to_number', '—')}")
        print(f"Резюме: {analysis['summary']}")
        if analysis.get("risk_flags"):
            print(f"Риски: {analysis['risk_flags']}")

        topic_id = find_or_create_topic(cur, analysis)
        email_db_id = save_email(cur, em, analysis, topic_id)
        conn.commit()

        update_graph(driver, em, analysis, topic_id, email_db_id, sender_name, cur)

        cur.execute("SELECT id, title, object_name FROM topics ORDER BY id")
        existing_topics = cur.fetchall()

    print(f"\n{'='*50}")
    print("Автоматическое слияние тем...")
    auto_merge_topics(conn, driver)

    print("\nИтоговые темы:")
    cur.execute("""
        SELECT t.id, t.title, t.object_name, count(e.id)
        FROM topics t
        LEFT JOIN emails e ON e.topic_id = t.id
        GROUP BY t.id ORDER BY t.id
    """)
    for row in cur.fetchall():
        print(f"  ID {row[0]}: '{row[1]}' (объект: {row[2]}) — {row[3]} писем")

    cur.close()
    conn.close()
    driver.close()

def check_processed(cur, message_id):
    cur.execute(
        "SELECT id FROM emails WHERE message_id = %s AND processed = TRUE",
        (message_id,)
    )
    return cur.fetchone() is not None

process_all()