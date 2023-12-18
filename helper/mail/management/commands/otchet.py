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
        cursor.execute("""SELECT   
                             t.tn, 
                             t.title, 
                             c.company_name, 
                             c.full_name, 
                             c.login, 
                             t.create_time, 
                             ts.comments AS "ticket_state", 
                             REPLACE(s.name, 'Поддержка прикладного ПО::Специальное программное обеспечение::', '') AS "service", 
                             q.name AS "queue"  
                              
                            FROM   
                             report.v_fact_ticket_v2 t 
                             join report.v_dim_client c ON t.customer_user_id = c.login 
                             join public.ticket_state ts on t.ticket_state_id = ts.id 
                             join public.service s on t.service_id = s.id 
                             join public.queue q on t.queue_id = q.id 
                              
                            WHERE   
                             c.lvl2 LIKE '%78%' AND c.lvl3 LIKE '%78%' -- номер региона 
                             AND t.ticket_state_id = ANY (ARRAY[1,15,14,4,6,13]) -- выбираем незакрытые 
                              
                            ORDER BY t.id DESC  
                            LIMIT 1000
                    """
                    )
        row = cursor.fetchall()
        print("Total rows are:  ", len(row))
        rows = cursor.fetchone()
        print(rows)
        cursor.close()
        connect.close()

