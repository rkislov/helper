import psycopg2
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings as django_settings
import os
import csv
import datetime
import xlsxwriter
from mail.models import Region, Topic
from helper.tasks import send_otchet_email_task
import pandas as pd


def generate_otchet(region_number):
    region = Region.objects.filter(region_number=region_number).first()

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

    filename = f"region-{region_number}-{datetime.date.today().isoformat()}.xlsx"
    subject = f"region-{region_number}-{datetime.date.today().isoformat()}"
    message = f"""Добрый день.

Во вложении отчет по заявкам по региону №{region_number}  на {datetime.date.today().isoformat()} 
    
    
Служба поддержки ЦП
Телефон: 8-800-301-23-39 
E-mail:  supportcp@cloud.rt.ru
    """
    fields = ['Номер заявки', 'Тема заявки', 'ИКСРФ/ТИК', 'ФИО Заявителя', 'email заявителя', 'Дата', 'Статус',
              'линия ТП', 'Комментарий']
    search_region = f"'%{region.region_number}%'"
    print(search_region)

    cursor = connect.cursor()
    sql=f"""
   SELECT 
   t.tn,  
   t.title,  
   c.company_name,  
   c.full_name,  
   c.login,  
   t.create_time,  
   ts.comments AS "ticket_state",  
   q.name AS "queue",
   (
   SELECT
   a.a_body 
   FROM
   report.v_fact_article a
   WHERE
   a.ticket_id = t.id
   AND a.article_type <> 'SystemNote'
   AND a.is_visible_for_customer = 1
   AND a.article_sender_type = 'agent'
   AND a.a_body NOT LIKE '%->%'                    
   ORDER BY a.id DESC
   LIMIT 1) AS "comment" FROM public.ticket t join report.v_dim_client c ON t.customer_user_id = c.login  
   join public.ticket_state ts on t.ticket_state_id = ts.id  
   join public.queue q on t.queue_id = q.id                        
   WHERE    
   c.lvl2 LIKE {search_region} AND c.lvl3 LIKE {search_region} -- номер региона  
   AND t.ticket_state_id = ANY (ARRAY[1,15,14,4,6,13]) -- выбираем незакрытые                        
   ORDER BY t.id DESC   
   LIMIT 1000"""
    cursor.execute(sql)
    rows = cursor.fetchall()
    print("Total rows are:  ", len(rows))
    path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()
    format1 = workbook.add_format({'bg_color': '#D9D9D9', 'bold': True})
    row = 0
    col = 0
    for f in fields:
        worksheet.write(row, col, f, format1)
        col +=1
    row += 1
    col = 0
    for ro in rows:
        date_time = f"{ro[5]}"
        worksheet.write(row, col, ro[0])
        worksheet.write(row, col + 1, ro[1])
        worksheet.write(row, col + 2, ro[2])
        worksheet.write(row, col + 3, ro[3])
        worksheet.write(row, col + 4, ro[4])
        worksheet.write(row, col + 5, date_time)
        worksheet.write(row, col + 6, ro[6])
        worksheet.write(row, col + 7, ro[7])
        if ro[8] != None:
            worksheet.write(row, col + 8, ro[8].strip())
        row += 1
        col = 0
    worksheet.autofit()
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, 1000, 8)
    #worksheet.set_default_row(50)
    workbook.close()
    send_otchet_email_task.delay([region.region_admin_email], subject, 'post@cifro.tech', message, filename)


def create_fullotchet(topic):


    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

    filename = f"{topic.slug}-{datetime.date.today().isoformat()}.xlsx"
    subject = f"{topic.slug}-{datetime.date.today().isoformat()}"


    message = f"""Добрый день.
Во вложении полный отчет по заявкам  на {datetime.date.today().isoformat()}


Служба поддержки ЦП
Телефон: 8-800-301-23-39
E-mail:  supportcp@cloud.rt.ru
     """


    cursor = connect.cursor()
    sql = f"""
    SELECT * 
    FROM report.v_try_report
    LIMIT 1000
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(rows[0])
    print("Total rows are:  ", len(rows))


    fields = ['№ п/п', 'Дата поступления', 'Время поступления', 'Номер обращения', 'Заявитель (фамилия и инициалы)',
              'Название субъекта РФ', 'Номер СТД (КСА)', 'Текст обращения', 'Классификация обращения',
              'Приоритет обращения',
              'Наименование подсистемы', 'Исполнитель обращения', 'Текущий статус', 'Описание оказанной консультации',
              'Необходимость модификации СПО', 'Номер листа внимания', 'дата закрытия', 'Время закрытия',
              'Общее время обработки', 'Канал поступления']

    fields2 =['Статус', 'Количество']
    path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()
    worksheet2 = workbook.add_worksheet()
    format1 = workbook.add_format({'bg_color': '#D9D9D9', 'bold': True})
    row = 0
    col = 0
    row2 = 0
    col2 = 0
    for f in fields:
        worksheet.write(row, col, f, format1)
        col += 1
    row += 1
    col = 0
    for f in fields2:
        worksheet2.write(row2, col2, f, format1)
        col2 += 1
    row2 += 1
    col2 = 0
    dict = {}
    if topic.slug == 'all':
        for ro in rows:
            worksheet.write(row, col, ro[0])
            worksheet.write(row, col + 1, ro[1])
            worksheet.write(row, col + 2, ro[2])
            worksheet.write(row, col + 3, ro[3])
            worksheet.write(row, col + 4, ro[4])
            worksheet.write(row, col + 5, ro[5])
            worksheet.write(row, col + 6, ro[6])
            worksheet.write(row, col + 7, ro[7])
            worksheet.write(row, col + 8, ro[8])
            worksheet.write(row, col + 9, ro[9])
            worksheet.write(row, col + 10, ro[10])
            worksheet.write(row, col + 11, ro[11])
            worksheet.write(row, col + 12, ro[12])
            worksheet.write(row, col + 13, ro[13])
            worksheet.write(row, col + 14, ro[14])
            worksheet.write(row, col + 15, ro[15])
            worksheet.write(row, col + 16, ro[16])
            worksheet.write(row, col + 17, ro[17])
            worksheet.write(row, col + 18, ro[18])
            worksheet.write(row, col + 19, ro[19])
            row += 1
            col = 0
            if ro[12] not in dict:
                dict[ro[12]] = 1
            else:
                dict[ro[12]] += 1
    else:
        for ro in rows:
            if ro[10] == topic.name:
                worksheet.write(row, col, ro[0])
                worksheet.write(row, col + 1, ro[1])
                worksheet.write(row, col + 2, ro[2])
                worksheet.write(row, col + 3, ro[3])
                worksheet.write(row, col + 4, ro[4])
                worksheet.write(row, col + 5, ro[5])
                worksheet.write(row, col + 6, ro[6])
                worksheet.write(row, col + 7, ro[7])
                worksheet.write(row, col + 8, ro[8])
                worksheet.write(row, col + 9, ro[9])
                worksheet.write(row, col + 10, ro[10])
                worksheet.write(row, col + 11, ro[11])
                worksheet.write(row, col + 12, ro[12])
                worksheet.write(row, col + 13, ro[13])
                worksheet.write(row, col + 14, ro[14])
                worksheet.write(row, col + 15, ro[15])
                worksheet.write(row, col + 16, ro[16])
                worksheet.write(row, col + 17, ro[17])
                worksheet.write(row, col + 18, ro[18])
                worksheet.write(row, col + 19, ro[19])
                row += 1
                col = 0
                if ro[12] not in dict:
                    dict[ro[12]] = 1
                else:
                    dict[ro[12]] += 1
    worksheet.autofit()
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, 1000, 20)
    worksheet.set_default_row(50)
    print(dict)
    for key, value in dict.items():
         worksheet2.write(row2, col2, key)
         worksheet2.write(row2, col2 + 1, value)
         row2 += 1
         col2 = 0
    worksheet.autofit()
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, 1000, 2)
    worksheet.set_default_row(50)
    workbook.close()

    emails = []
    iteremails = topic.recivers.all()
    print(iteremails[0])
    for email in iteremails:
        emails.append(email.email)
    print(emails)
    print(filename)
    df = pd.DataFrame([sub.split(",") for sub in rows], columns=fields)
    print(df)
    #send_otchet_email_task.delay(emails, subject, 'post@cifro.tech', message, filename)




