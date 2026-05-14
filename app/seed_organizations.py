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

# Организации
organizations = [
    ("МонотекСтрой", "genpodryad", "monotekstroy.ru"),
    ("СтройИнвест", "zakazchik", "stroyinvest.ru"),
    ("ГПИ-7", "proektirovshik", "gpi7.ru"),
]

cur.executemany("""
    INSERT INTO organizations (name, type, domain)
    VALUES (%s, %s, %s)
    ON CONFLICT DO NOTHING
""", organizations)

conn.commit()

# Получаем ID организаций
cur.execute("SELECT id, name FROM organizations ORDER BY id")
orgs = {row[1]: row[0] for row in cur.fetchall()}
print(f"Организации: {orgs}")

# Внешние контакты
contacts = [
    ("Иванов Сергей Петрович",   "ivanov@stroyinvest.ru",  orgs["СтройИнвест"]),
    ("Смирнова Анна Васильевна", "smirnova@stroyinvest.ru", orgs["СтройИнвест"]),
    ("Гусев Николай Борисович",  "gusev@gpi7.ru",          orgs["ГПИ-7"]),
    ("Павлова Ирина Олеговна",   "pavlova@gpi7.ru",        orgs["ГПИ-7"]),
]

cur.executemany("""
    INSERT INTO external_contacts (name, email, organization_id)
    VALUES (%s, %s, %s)
    ON CONFLICT (email) DO NOTHING
""", contacts)

conn.commit()
print(f"Внешние контакты добавлены")

cur.execute("""
    SELECT ec.name, ec.email, o.name
    FROM external_contacts ec
    JOIN organizations o ON ec.organization_id = o.id
    ORDER BY o.id
""")
for row in cur.fetchall():
    print(f"  {row[0]} ({row[1]}) — {row[2]}")

cur.close()
conn.close()