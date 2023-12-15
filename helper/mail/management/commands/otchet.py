import psycopg2
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
load_dotenv()
import os


class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"), password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"), port=os.getenv("DBE_PORT"))

        cursor = connect.cursor()
        cursor.execute("SELECT * FROM public.ticket ORDER BY id DESC LIMIT 10")
        row = cursor.fetchone()
        cursor.close()
        connect.close()
        print(row)
