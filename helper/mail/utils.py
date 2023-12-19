import psycopg2
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings as django_settings
import os
import csv
import datetime
import xlsxwriter
from mail.models import Region
from helper.tasks import send_otchet_email_task


def generate_otchet(region_number):
    region = Region.objects.filter(region_number=region_number).first()

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

    filename = f"region-{region_number}-{datetime.date.today().isoformat()}.xlsx"
    subject = f"region-{region_number}-{datetime.date.today().isoformat()}"
    #message = f"напраялю отчет по заявкам за по региону №{region_number} за {datetime.date.today().isoformat()} "
    message = f"""Добрый день.

Во вложении отчет по заявкам по региону №{region_number}  на {datetime.date.today().isoformat()} 
    
    
Служба поддержки ЦП
Телефон: 8-800-301-23-39 
E-mail:  supportcp@cloud.rt.ru
    """
    fields = ['Номер заявки', 'Тема заявки', 'ИКСРФ/ТИК', 'ФИО Заявителя', 'email заявителя', 'Дата', 'Статус',
              'линия ТП']
    search_region = f"%{region.region_number}%"
    print(search_region)
    cursor = connect.cursor()
    cursor.execute("""SELECT    
                             t.tn,  
                             t.title,  
                             c.company_name,  
                             c.full_name,  
                             c.login,  
                             t.create_time,  
                             ts.comments AS "ticket_state",  
                             q.name AS "queue"   
                               
                            FROM    
                             report.v_fact_ticket_v2 t  
                             join report.v_dim_client c ON t.customer_user_id = c.login  
                             join public.ticket_state ts on t.ticket_state_id = ts.id  
                             join public.queue q on t.queue_id = q.id  
                               
                            WHERE    
                             c.lvl2 LIKE (%s) AND c.lvl3 LIKE (%s) -- номер региона  
                             AND t.ticket_state_id = ANY (ARRAY[1,15,14,4,6,13]) -- выбираем незакрытые  
                               
                            ORDER BY t.id DESC   
                            LIMIT 1000
                       """, (search_region, search_region))
    rows = cursor.fetchall()
    print("Total rows are:  ", len(rows))
    path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    #print(row[0])
    #print(row[1])
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})
    row = 0
    col = 0
    for f in fields:
        worksheet.write(row, col, f, bold)
        col +=1
    row += 1
    col = 0
    # print(tuple_to_list(row))
    #with open(os.path.join(django_settings.STATIC_ROOT, f'{filename}'), 'w') as f:
    #    csv_writer = csv.writer(f)
    #    csv_writer.writerow(fields)
    #format1 = workbook.add_format({'num_format': 'dd.mm.yy hh:mm'})
    for ro in rows:
        date_time = f"{ro[5]}"
        #print(date_time)
        worksheet.write(row, col, ro[0])
        worksheet.write(row, col + 1, ro[1])
        worksheet.write(row, col + 2, ro[2])
        worksheet.write(row, col + 3, ro[3])
        worksheet.write(row, col + 4, ro[4])
        worksheet.write(row, col + 5, date_time)
        worksheet.write(row, col + 6, ro[6])
        worksheet.write(row, col + 7, ro[7])
        row += 1
        col = 0
    worksheet.autofit()
    workbook.close()
    send_otchet_email_task.delay([region.region_admin_email], subject, 'post@cifro.tech', message, filename)
