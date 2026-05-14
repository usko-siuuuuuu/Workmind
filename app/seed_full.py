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

# Очищаем старые данные
cur.execute("DELETE FROM external_contacts")
cur.execute("DELETE FROM organizations")
cur.execute("DELETE FROM employees")
conn.commit()

# Организации
organizations = [
    ("МонотекСтрой", "genpodryad", "monotekstroy.ru"),
    ("ИнвестСтрой Групп", "zakazchik", "investstroy.ru"),
    ("ГПИ Проект", "proektirovshik", "gpiproekt.ru"),
    ("ФасадТех", "subpodryad", "fasadtech.ru"),
    ("ИнтерьерСтрой", "subpodryad", "interstroy.ru"),
]

cur.executemany("""
    INSERT INTO organizations (name, type, domain)
    VALUES (%s, %s, %s)
""", organizations)
conn.commit()

cur.execute("SELECT id, name, domain FROM organizations ORDER BY id")
orgs = {row[1]: (row[0], row[2]) for row in cur.fetchall()}
print("Организации созданы:")
for name, (org_id, domain) in orgs.items():
    print(f"  [{org_id}] {name} ({domain})")

# Сотрудники МонотекСтрой — 40 человек
monotek_employees = [
    # Руководство
    ("Тихонов Владимир Борисович",      "tikhonov@monotekstroy.ru",       "Генеральный директор"),
    ("Козлов Алексей Иванович",         "kozlov@monotekstroy.ru",         "Главный инженер проекта (ГИП)"),
    ("Петров Игорь Васильевич",         "petrov@monotekstroy.ru",         "Руководитель проекта — ТЦ Галактика"),
    ("Романова Светлана Андреевна",     "romanova@monotekstroy.ru",       "Руководитель проекта — МЦ Здоровье"),
    ("Захаров Денис Юрьевич",          "zakharov@monotekstroy.ru",       "Руководитель проекта — Апарт-отель Аврора"),
    # ПТО
    ("Иванова Мария Сергеевна",         "ivanova@monotekstroy.ru",        "Главный инженер ПТО"),
    ("Смирнов Артём Олегович",          "smirnov@monotekstroy.ru",        "Инженер ПТО — ТЦ Галактика"),
    ("Белова Екатерина Николаевна",     "belova@monotekstroy.ru",         "Инженер ПТО — МЦ Здоровье"),
    ("Крылов Павел Дмитриевич",         "krylov@monotekstroy.ru",         "Инженер ПТО — Апарт-отель Аврора"),
    # Начальники участков
    ("Сидоров Дмитрий Олегович",        "sidorov@monotekstroy.ru",        "Начальник участка — ТЦ Галактика"),
    ("Фёдоров Николай Петрович",        "fedorov@monotekstroy.ru",        "Начальник участка — МЦ Здоровье"),
    ("Громов Сергей Александрович",     "gromov@monotekstroy.ru",         "Начальник участка — Апарт-отель Аврора"),
    # Прорабы
    ("Лебедев Сергей Михайлович",       "lebedev@monotekstroy.ru",        "Прораб — ТЦ Галактика (фасад)"),
    ("Орлов Виктор Фёдорович",          "orlov@monotekstroy.ru",          "Прораб — ТЦ Галактика (внутренние работы)"),
    ("Васильев Игорь Сергеевич",        "vasiliev@monotekstroy.ru",       "Прораб — МЦ Здоровье"),
    ("Морозов Андрей Викторович",       "morozov@monotekstroy.ru",        "Прораб — Апарт-отель Аврора"),
    # Инженеры
    ("Новикова Елена Павловна",         "novikova@monotekstroy.ru",       "Инженер по качеству"),
    ("Кузнецов Роман Евгеньевич",       "kuznetsov@monotekstroy.ru",      "Геодезист"),
    ("Фёдоров Максим Александрович",    "fedorov.m@monotekstroy.ru",      "Инженер ОТ и ТБ"),
    ("Попов Андрей Игоревич",           "popov@monotekstroy.ru",          "Инженер по сварке"),
    ("Зайцев Константин Борисович",     "zaitsev@monotekstroy.ru",        "Инженер-механик"),
    # Сметный отдел
    ("Новикова Ирина Александровна",    "novikova.i@monotekstroy.ru",     "Главный сметчик"),
    ("Тарасова Юлия Викторовна",        "tarasova@monotekstroy.ru",       "Сметчик — ТЦ Галактика"),
    ("Михайлов Денис Олегович",         "mikhailov@monotekstroy.ru",      "Сметчик — МЦ Здоровье"),
    ("Степанова Анна Сергеевна",        "stepanova@monotekstroy.ru",      "Сметчик — Апарт-отель Аврора"),
    # Снабжение
    ("Соколов Павел Андреевич",         "sokolov@monotekstroy.ru",        "Начальник отдела снабжения"),
    ("Попова Анна Игоревна",            "popova@monotekstroy.ru",         "Менеджер по закупкам"),
    ("Борисов Алексей Юрьевич",         "borisov@monotekstroy.ru",        "Менеджер по логистике"),
    # Юридический отдел
    ("Волкова Ольга Николаевна",        "volkova@monotekstroy.ru",        "Главный юрист"),
    ("Матвеев Сергей Владимирович",     "matveev@monotekstroy.ru",        "Юрист по договорной работе"),
    # Бухгалтерия
    ("Захарова Наталья Дмитриевна",     "zakharova@monotekstroy.ru",      "Главный бухгалтер"),
    ("Семёнова Ирина Петровна",         "semenova@monotekstroy.ru",       "Бухгалтер"),
    # Делопроизводство
    ("Орлова Светлана Юрьевна",         "orlova@monotekstroy.ru",         "Начальник отдела документооборота"),
    ("Павлова Дарья Алексеевна",        "pavlova@monotekstroy.ru",        "Делопроизводитель"),
    # ИД и исполнительная документация
    ("Громова Татьяна Сергеевна",       "gromova@monotekstroy.ru",        "Инженер по исполнительной документации"),
    ("Никитин Александр Павлович",      "nikitin@monotekstroy.ru",        "Инженер по исполнительной документации"),
    # Проектный отдел
    ("Соловьёв Михаил Андреевич",       "soloviev@monotekstroy.ru",       "Главный архитектор проекта"),
    ("Киселёва Анна Борисовна",         "kiseleva@monotekstroy.ru",       "Архитектор"),
    # Охрана труда
    ("Куликов Иван Петрович",           "kulikov@monotekstroy.ru",        "Специалист по охране труда"),
    ("Фролова Марина Викторовна",       "frolova@monotekstroy.ru",        "Инженер по экологии и охране труда"),
]

cur.executemany("""
    INSERT INTO employees (name, email, position)
    VALUES (%s, %s, %s)
    ON CONFLICT (email) DO NOTHING
""", monotek_employees)
conn.commit()
print(f"\nСотрудники МонотекСтрой: {len(monotek_employees)}")

# Внешние контакты — заказчик ИнвестСтрой Групп
zakazchik_id = orgs["ИнвестСтрой Групп"][0]
zakazchik_contacts = [
    ("Громов Александр Петрович",       "gromov@investstroy.ru",          zakazchik_id, "Генеральный директор"),
    ("Иванов Сергей Петрович",          "ivanov@investstroy.ru",          zakazchik_id, "Директор по строительству"),
    ("Смирнова Анна Васильевна",        "smirnova@investstroy.ru",        zakazchik_id, "Руководитель проектов"),
    ("Лукьянов Дмитрий Игоревич",       "lukyanov@investstroy.ru",        zakazchik_id, "Технический надзор"),
    ("Фомина Екатерина Олеговна",       "fomina@investstroy.ru",          zakazchik_id, "Юрист"),
]

# Проектировщик ГПИ Проект
proekt_id = orgs["ГПИ Проект"][0]
proekt_contacts = [
    ("Гусев Николай Борисович",         "gusev@gpiproekt.ru",             proekt_id,    "Главный инженер проекта"),
    ("Павлова Ирина Олеговна",          "pavlova@gpiproekt.ru",           proekt_id,    "Архитектор"),
    ("Рогов Алексей Сергеевич",         "rogov@gpiproekt.ru",             proekt_id,    "Конструктор"),
    ("Зимина Наталья Викторовна",       "zimina@gpiproekt.ru",            proekt_id,    "Инженер по вентиляции"),
    ("Харитонов Борис Андреевич",       "kharitonov@gpiproekt.ru",        proekt_id,    "Инженер-электрик"),
    ("Лазарева Юлия Михайловна",        "lazareva@gpiproekt.ru",          proekt_id,    "Инженер ВК"),
    ("Орехов Сергей Павлович",          "orekhov@gpiproekt.ru",           proekt_id,    "ГИП"),
]

# Субподрядчик 1 — ФасадТех
fasad_id = orgs["ФасадТех"][0]
fasad_contacts = [
    ("Беляев Виктор Николаевич",        "belyaev@fasadtech.ru",           fasad_id,     "Генеральный директор"),
    ("Козырев Андрей Сергеевич",        "kozyrev@fasadtech.ru",           fasad_id,     "Руководитель проекта"),
    ("Максимов Илья Олегович",          "maksimov@fasadtech.ru",          fasad_id,     "Прораб"),
    ("Герасимова Оксана Петровна",      "gerasimova@fasadtech.ru",        fasad_id,     "Сметчик"),
    ("Антонов Павел Игоревич",          "antonov@fasadtech.ru",           fasad_id,     "Инженер по качеству"),
    ("Тимофеев Алексей Борисович",      "timofeev@fasadtech.ru",          fasad_id,     "Мастер участка"),
    ("Власова Светлана Дмитриевна",     "vlasova@fasadtech.ru",           fasad_id,     "Менеджер по снабжению"),
    ("Крюков Дмитрий Александрович",    "kryukov@fasadtech.ru",           fasad_id,     "Инженер ПТО"),
    ("Абрамова Надежда Сергеевна",      "abramova@fasadtech.ru",          fasad_id,     "Бухгалтер"),
]

# Субподрядчик 2 — ИнтерьерСтрой
inter_id = orgs["ИнтерьерСтрой"][0]
inter_contacts = [
    ("Никифоров Евгений Борисович",     "nikiforov@interstroy.ru",        inter_id,     "Генеральный директор"),
    ("Панов Сергей Викторович",         "panov@interstroy.ru",            inter_id,     "Руководитель проекта"),
    ("Горбунов Алексей Николаевич",     "gorbunov@interstroy.ru",         inter_id,     "Прораб по отделке"),
    ("Зубова Марина Петровна",          "zubova@interstroy.ru",           inter_id,     "Сметчик"),
    ("Ершов Константин Сергеевич",      "ershov@interstroy.ru",           inter_id,     "Инженер по качеству"),
    ("Логинова Татьяна Андреевна",      "loginova@interstroy.ru",         inter_id,     "Менеджер по снабжению"),
    ("Щербаков Павел Олегович",         "shcherbakov@interstroy.ru",      inter_id,     "Инженер ПТО"),
    ("Мельникова Юлия Сергеевна",       "melnikova@interstroy.ru",        inter_id,     "Делопроизводитель"),
    ("Воронов Игорь Дмитриевич",        "voronov@interstroy.ru",          inter_id,     "Мастер участка"),
    ("Тихомирова Анна Борисовна",       "tikhomirova@interstroy.ru",      inter_id,     "Бухгалтер"),
    ("Кириллов Максим Андреевич",       "kirillov@interstroy.ru",         inter_id,     "Инженер ОТ и ТБ"),
    ("Суворова Елена Викторовна",       "suvorova@interstroy.ru",         inter_id,     "Юрист"),
]

all_contacts = zakazchik_contacts + proekt_contacts + fasad_contacts + inter_contacts

cur.executemany("""
    INSERT INTO external_contacts (name, email, organization_id)
    VALUES (%s, %s, %s)
    ON CONFLICT (email) DO NOTHING
""", [(c[0], c[1], c[2]) for c in all_contacts])
conn.commit()

print(f"Заказчик ИнвестСтрой Групп: {len(zakazchik_contacts)} сотрудников")
print(f"Проектировщик ГПИ Проект: {len(proekt_contacts)} сотрудников")
print(f"Субподрядчик ФасадТех: {len(fasad_contacts)} сотрудников")
print(f"Субподрядчик ИнтерьерСтрой: {len(inter_contacts)} сотрудников")
print(f"Итого внешних контактов: {len(all_contacts)}")

# Должности внешних контактов в отдельную таблицу (через поле notes пока)
cur.execute("ALTER TABLE external_contacts ADD COLUMN IF NOT EXISTS position VARCHAR(200)")
conn.commit()

for contact in all_contacts:
    cur.execute("""
        UPDATE external_contacts SET position = %s WHERE email = %s
    """, (contact[3], contact[1]))
conn.commit()

cur.close()
conn.close()
print("\nВсе данные записаны успешно!")