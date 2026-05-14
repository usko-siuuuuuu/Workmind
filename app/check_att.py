import psycopg2
from dotenv import load_dotenv
import os
load_dotenv('C:/workmind/.env')
conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST'), port=os.getenv('POSTGRES_PORT'), user=os.getenv('POSTGRES_USER'), password=os.getenv('POSTGRES_PASSWORD'), dbname=os.getenv('POSTGRES_DB'))
cur = conn.cursor()
cur.execute("SELECT subject, attachments_text FROM emails WHERE attachments_text IS NOT NULL AND attachments_text != '' LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print(r[0], '|', r[1][:100])
print(f"Итого писем с вложениями: {len(rows)}")