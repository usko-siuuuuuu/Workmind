from neo4j import GraphDatabase
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="C:/workmind/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    dbname=os.getenv("POSTGRES_DB")
)
cur = conn.cursor()

cur.execute("""
    SELECT e.email, e.name, t.title, t.priority, t.source,
           em.sender, em.subject
    FROM tasks t
    JOIN employees e ON t.employee_id = e.id
    JOIN emails em ON em.id = (
        SELECT id FROM emails ORDER BY received_at DESC LIMIT 1
    )
""")

rows = cur.fetchall()

with driver.session() as session:
    for email, name, title, priority, source, sender, subject in rows:
        session.run("""
            MERGE (e:Employee {email: $email})
            MERGE (s:Contact {email: $sender})
            MERGE (t:Task {title: $title, assignee: $email})
                SET t.priority = $priority
            MERGE (letter:Email {subject: $subject})
            MERGE (s)-[:SENT]->(letter)
            MERGE (letter)-[:CREATED]->(t)
            MERGE (t)-[:ASSIGNED_TO]->(e)
        """, email=email, sender=sender, title=title,
             priority=priority, subject=subject)
        print(f"Связь: {sender} → {subject} → {title} → {name}")

print("\nГраф обновлён!")

cur.close()
conn.close()
driver.close()