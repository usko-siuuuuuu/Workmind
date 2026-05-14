import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="C:/workmind/.env")

# Сброс PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    dbname=os.getenv("POSTGRES_DB")
)
cur = conn.cursor()
cur.execute("UPDATE emails SET topic_id = NULL, processed = FALSE")
cur.execute("DELETE FROM topics")
cur.execute("DELETE FROM documents")
conn.commit()
cur.close()
conn.close()
print("PostgreSQL сброшен")

# Сброс графа — удаляем только письма и темы, людей и организации не трогаем
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
with driver.session() as session:
    session.run("MATCH (e:Email) DETACH DELETE e")
    session.run("MATCH (t:Topic) DETACH DELETE t")
    print("Neo4j сброшен — письма и темы удалены")
    
    result = session.run("MATCH (p:Person) RETURN count(p) as count")
    print(f"Людей в графе осталось: {result.single()['count']}")

driver.close()