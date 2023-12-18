import psycopg2
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings as django_settings
import os
import csv
import datetime
from mail.models import Region
from helper.tasks import send_otchet_email_task


def generate_otchet(region_number):
    region = Region.objects.filter(region_number=region_number).first()

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

    filename = f"region-{region_number}-{datetime.date.today().isoformat()}.csv"
    subject = f"region-{region_number}-{datetime.date.today().isoformat()}"
    message = f"напраялю отчет по заявкам за по региону №{region_number} за {datetime.date.today().isoformat()} "
    fields = ['Номер заявки', 'Заявитель', 'ТИК', 'ФИО Заявителя', 'email заявителя', 'Дата', 'Статус', 'СПО',
              'линия ТП']
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
                                c.lvl2 LIKE %(%s)% AND c.lvl3 LIKE %(%s)% -- номер региона 
                                AND t.ticket_state_id = ANY (ARRAY[1,15,14,4,6,13]) -- выбираем незакрытые 

                               ORDER BY t.id DESC  
                               LIMIT 1000
                       """, (78, 78)
                   )
    row = cursor.fetchall()
    print("Total rows are:  ", len(row))

    #print(row[0])
    #print(row[1])

    # print(tuple_to_list(row))
    with open(os.path.join(django_settings.STATIC_ROOT, f'{filename}'), 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(fields)
        for ro in row:
            csv_writer.writerow(list(ro))

    send_otchet_email_task.delay([region.region_admin_email], subject, 'post@cifro.tech', message, filename)
