import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="C:/workmind/.env")

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    dbname=os.getenv("POSTGRES_DB")
)
cur = conn.cursor()
cur.execute("DELETE FROM tasks")
cur.execute("DELETE FROM email_relations")
cur.execute("DELETE FROM documents")
cur.execute("UPDATE emails SET topic_id = NULL, processed = FALSE")
cur.execute("DELETE FROM topics")
cur.execute("DELETE FROM emails")
cur.execute("DELETE FROM external_contacts")
cur.execute("DELETE FROM organizations")
cur.execute("DELETE FROM employees")
conn.commit()
cur.close()
conn.close()
print("PostgreSQL сброшен полностью")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
    print("Neo4j сброшен полностью")
driver.close()