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

with driver.session() as session:

    # Организации
    cur.execute("SELECT name, type, domain FROM organizations")
    for name, org_type, domain in cur.fetchall():
        session.run("""
            MERGE (o:Organization {domain: $domain})
            SET o.name = $name, o.type = $type
        """, domain=domain, name=name, type=org_type)
    print("Организации созданы")

    # Наши сотрудники — единый узел Person с меткой Employee
    cur.execute("SELECT name, email, position FROM employees")
    for name, email, position in cur.fetchall():
        session.run("""
            MERGE (p:Person {email: $email})
            SET p.name = $name,
                p.position = $position,
                p.internal = true
            WITH p
            MATCH (o:Organization {domain: 'monotekstroy.ru'})
            MERGE (p)-[:WORKS_AT]->(o)
        """, email=email, name=name, position=position)
    print("Сотрудники МонотекСтрой созданы")

    # Внешние контакты — тоже Person
    cur.execute("""
        SELECT ec.name, ec.email, o.domain
        FROM external_contacts ec
        JOIN organizations o ON ec.organization_id = o.id
    """)
    for name, email, domain in cur.fetchall():
        session.run("""
            MERGE (p:Person {email: $email})
            SET p.name = $name,
                p.internal = false
            WITH p
            MATCH (o:Organization {domain: $domain})
            MERGE (p)-[:WORKS_AT]->(o)
        """, email=email, name=name, domain=domain)
    print("Внешние контакты созданы")

    # Проверка
    result = session.run("""
        MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
        RETURN o.name as org, count(p) as people
        ORDER BY o.name
    """)
    print("\nИтог:")
    for row in result:
        print(f"  {row['org']}: {row['people']} человек")

cur.close()
conn.close()
driver.close()