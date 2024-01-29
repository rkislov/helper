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


def generate_topic(filename, topic):
    df = pd.read_excel(filename)
    for service in topic.services:
        message = f"""Добрый день.
         Во вложении полный отчет по сервису {topic.name}  на {datetime.date.today().isoformat()}

        Служба поддержки ЦП
        Телефон: 8-800-301-23-39
        E-mail:  supportcp@cloud.rt.ru
             """
        df_rows = df[df['Наименование подсистемы'] == service.name]
        rows = []
        emails = []
        iteremails = topic.recivers.all()
        for email in iteremails:
            rows.append(email.email)

        newfilename = f"{service.name}-{datetime.date.today().isoformat()}.xlsx"
        newsubject = f"{service.name}-{datetime.date.today()}"
        for row in df_rows.itterows():
            rows.append(row)
            worksheet = make_file(newfilename, rows)
            send_otchet_email_task.delay(emails, newsubject, 'post@cifro.tech', message, worksheet)

def make_file(filename, rows):
    fields = ['№ п/п', 'Дата поступления', 'Время поступления', 'Номер обращения', 'Заявитель (фамилия и инициалы)',
              'Название субъекта РФ', 'Номер СТД (КСА)', 'Текст обращения', 'Классификация обращения',
              'Приоритет обращения',
              'Наименование подсистемы', 'Исполнитель обращения', 'Текущий статус', 'Описание оказанной консультации',
              'Необходимость модификации СПО', 'Номер листа внимания', 'дата закрытия', 'Время закрытия',
              'Общее время обработки', 'Канал поступления']

    path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()
    format1 = workbook.add_format({'bg_color': '#D9D9D9', 'bold': True})
    row = 0
    col = 0
    for f in fields:
        worksheet.write(row, col, f, format1)
        col += 1
    row += 1
    col = 0
    for ro in rows:
        date_time = f"{ro[5]}"
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
        # if ro[8] != None:
        #     worksheet.write(row, col + 8, ro[8].strip())
        row += 1
        col = 0
    worksheet.autofit()
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, 1000, 20)
    worksheet.set_default_row(50)
    workbook.close()
    return worksheet
def generate_fullotchet():
   # region = Region.objects.filter(region_number=region_number).first()

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

#     filename = f"region-{region_number}-{datetime.date.today().isoformat()}.xlsx"
#     subject = f"region-{region_number}-{datetime.date.today().isoformat()}"
#
#
    topic = Topic.objects.filter(slug='all').first()
    alltopics = Topic.objects.exclude(slug='all').all()
    filename = f"{topic.slug}-{datetime.date.today().isoformat()}.xlsx"
    subject = f"{topic.slug}-{datetime.date.today().isoformat()}"


    message = f"""Добрый день.
Во вложении полный отчет по заявкам  на {datetime.date.today().isoformat()}


Служба поддержки ЦП
Телефон: 8-800-301-23-39
E-mail:  supportcp@cloud.rt.ru
     """

#     search_region = f"'%{region.region_number}%'"
#     print(search_region)

    cursor = connect.cursor()
    sql = f"""
    SELECT * 
    FROM report.v_try_report
    LIMIT 1000
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    print("Total rows are:  ", len(rows))
    #print("Row 0: ", rows[0])
    worksheet = make_file(filename, rows)

    emails = []
    iteremails = topic.recivers.all()
    print(iteremails[0])
    for email in iteremails:
        emails.append(email.email)
    #path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    #send_otchet_email_task.delay([region.region_admin_email], subject, 'post@cifro.tech', message, filename)
    send_otchet_email_task.delay(emails, subject, 'post@cifro.tech', message, worksheet)

    for top in alltopics:
        generate_topic(worksheet, top)


