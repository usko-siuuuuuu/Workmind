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

cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    position VARCHAR(100),
    telegram_id BIGINT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id),
    title TEXT NOT NULL,
    description TEXT,
    source VARCHAR(20),
    priority VARCHAR(10) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    due_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(200) UNIQUE,
    sender VARCHAR(100),
    recipients TEXT,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);
""")

conn.commit()
cur.close()
conn.close()

print("Таблицы созданы успешно")