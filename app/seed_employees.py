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

employees = [
    ("Козлов Алексей Иванович",      "kozlov@monotekstroy.ru",      "ГИП"),
    ("Петров Игорь Васильевич",       "petrov@monotekstroy.ru",      "Руководитель проекта"),
    ("Иванова Мария Сергеевна",       "ivanova@monotekstroy.ru",     "Инженер ПТО"),
    ("Сидоров Дмитрий Олегович",      "sidorov@monotekstroy.ru",     "Начальник участка"),
    ("Новикова Елена Павловна",       "novikova@monotekstroy.ru",    "Сметчик"),
    ("Морозов Андрей Викторович",     "morozov@monotekstroy.ru",     "Инженер по качеству"),
    ("Волкова Ольга Николаевна",      "volkova@monotekstroy.ru",     "Юрист"),
    ("Соколов Павел Андреевич",       "sokolov@monotekstroy.ru",     "Снабженец"),
    ("Лебедев Сергей Михайлович",     "lebedev@monotekstroy.ru",     "Прораб"),
    ("Захарова Наталья Дмитриевна",   "zakharova@monotekstroy.ru",   "Бухгалтер"),
    ("Федоров Максим Александрович",  "fedorov@monotekstroy.ru",     "Инженер ОТ и ТБ"),
    ("Орлова Светлана Юрьевна",       "orlova@monotekstroy.ru",      "Делопроизводитель"),
    ("Кузнецов Роман Евгеньевич",     "kuznetsov@monotekstroy.ru",   "Геодезист"),
    ("Попова Анна Игоревна",          "popova@monotekstroy.ru",      "Менеджер по закупкам"),
    ("Тихонов Владимир Борисович",    "tikhonov@monotekstroy.ru",    "Директор"),
]

cur.executemany("""
    INSERT INTO employees (name, email, position)
    VALUES (%s, %s, %s)
    ON CONFLICT (email) DO NOTHING
""", employees)

conn.commit()
print(f"Добавлено сотрудников: {cur.rowcount}")

cur.execute("SELECT id, name, position FROM employees ORDER BY id")
for row in cur.fetchall():
    print(f"  [{row[0]}] {row[1]} — {row[2]}")

cur.close()
conn.close()