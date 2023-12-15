import psycopg2
from dotenv import load_dotenv
load_dotenv()
import os

connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"), password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"), port=os.getenv("DBE_PORT"))

cursor = connect.cursor()
row = cursor.fetchone()
cursor.close()
connect.close()
print(row)
