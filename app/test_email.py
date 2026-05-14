import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_email(from_email, to_emails, subject, body):
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("localhost", 1025) as server:
        server.sendmail(from_email, to_emails, msg.as_string())
    print(f"Письмо отправлено: {subject}")

# Тестовое письмо от заказчика к нескольким сотрудникам
send_test_email(
    from_email="zakazchik@stroy-invest.ru",
    to_emails=[
        "kozlov@monotekstroy.ru",
        "petrov@monotekstroy.ru",
        "sidorov@monotekstroy.ru"
    ],
    subject="Задержка геодезических работ на объекте №12",
    body="""Добрый день, коллеги.

Обращаем ваше внимание на недопустимую задержку геодезических работ на объекте №12.
Согласно договору №456 от 01.03.2025, срок выполнения работ истёк 15 апреля.

Козлов А.И. — прошу предоставить объяснительную записку и план устранения до 21 апреля.
Петров И.В. — прошу актуализировать график работ с учётом задержки.
Сидоров Д.О. — обеспечьте немедленный выход геодезистов на объект.

В случае непринятия мер в указанные сроки будем вынуждены применить штрафные санкции
согласно п.8.2 договора.

С уважением,
Иванов С.П.
ООО "СтройИнвест"
"""
)