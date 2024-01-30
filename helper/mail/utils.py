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


def create_fullotchet():


    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))




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

    df = pd.DataFrame(list(rows), columns=fields)




    topics = Topic.objects.all()

    for topic in topics:
        filename = f"{topic.slug}-{datetime.date.today().isoformat()}.xlsx"
        subject = f"{topic.slug}-{datetime.date.today().isoformat()}"
        path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
        if topic.slug == 'all':
            print(df)
            print(len(df.columns))
            print(len(df))

            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Заявки', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Заявки']
            worksheet.autofit()
            worksheet.freeze_panes(1, 0)
            for i, height in enumerate([25] * df.shape[0]):  # устанавливаем высоту строк
                worksheet.set_row(i, height)

            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            workbook.close()
        else:
            servis_df = df.loc[df['Наименование подсистемы'] == topic.name]
            print(servis_df)
            print(len(servis_df.columns))
            print(len(servis_df))
            counts = servis_df['Текущий статус'].value_counts()
            print(counts)
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            servis_df.to_excel(writer, sheet_name='Заявки', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Заявки']
            worksheet.autofit()
            worksheet.freeze_panes(1, 0)
            for i, height in enumerate([25] * servis_df.shape[0]):  # устанавливаем высоту строк
                worksheet.set_row(i, height)

            worksheet.autofilter(0, 0, len(servis_df), len(servis_df.columns) - 1)
            workbook.close()



        emails = []
        iteremails = topic.recivers.all()
        print(iteremails[0])
        for email in iteremails:
            emails.append(email.email)
        print(emails)
        print(filename)

        #send_otchet_email_task.delay(emails, subject, 'post@cifro.tech', message, filename)




