import psycopg2
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

# Внешние организации (заказчик, проектировщик и т д)
cur.execute("""
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),
    domain VARCHAR(100)
);
""")

# Внешние контакты (сотрудники заказчика, проектировщика)
cur.execute("""
CREATE TABLE IF NOT EXISTS external_contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    email VARCHAR(200) UNIQUE NOT NULL,
    organization_id INTEGER REFERENCES organizations(id)
);
""")

# Темы/цепочки согласований
cur.execute("""
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    object_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# Расширяем таблицу emails
cur.execute("""
ALTER TABLE emails
    ADD COLUMN IF NOT EXISTS outgoing_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS reply_to_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS topic_id INTEGER REFERENCES topics(id),
    ADD COLUMN IF NOT EXISTS email_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS smtp_port INTEGER;
""")

# Документы-вложения
cur.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id),
    filename VARCHAR(500),
    filepath VARCHAR(1000),
    filetype VARCHAR(50),
    extracted_text TEXT,
    outgoing_number VARCHAR(100),
    reply_to_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# Связи между письмами
cur.execute("""
CREATE TABLE IF NOT EXISTS email_relations (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id),
    related_email_id INTEGER REFERENCES emails(id),
    relation_type VARCHAR(50)
);
""")

conn.commit()
cur.close()
conn.close()
print("БД обновлена успешно")