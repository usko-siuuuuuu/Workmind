from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="C:/workmind/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

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

with driver.session() as session:
    for name, email, position in employees:
        session.run("""
            MERGE (e:Employee {email: $email})
            SET e.name = $name,
                e.position = $position
        """, name=name, email=email, position=position)

    print("Сотрудники добавлены в граф")

    result = session.run("MATCH (e:Employee) RETURN count(e) as count")
    print(f"Узлов в графе: {result.single()['count']}")

driver.close()