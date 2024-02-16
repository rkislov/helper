import psycopg2
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings as django_settings
import os
import datetime
import xlsxwriter
from mail.models import Region, Topic, FciTopic
from helper.tasks import send_otchet_email_task
import pandas as pd
import time
from sqlalchemy import create_engine


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
    start = time.time()
    cursor.execute(sql)
    end = time.time() - start
    print(end)
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

    date = datetime.date.today()
    time = datetime.time(18, 00)
    date_for_otchet = datetime.datetime.combine(date, time)
    date_for_otchet2 = f"'{date_for_otchet}'"
    message = f"""Добрый вечер, коллеги!

Во вложении общий отчёт по заявкам, которые идут в отчёт заказчику.
Период от: 2023-05-16 00:00:00
Период до: {date_for_otchet}

Отчёт составлен автоматически.
Вопросы по отчёту - taras.demchenko@rt.ru
     """
    print(date)
    print(date_for_otchet)
    print(date_for_otchet2)
    cursor = connect.cursor()
    sql = f"""
       SELECT  
     * 
    FROM  
     report.v_try_source_v2 t 
      
    WHERE   
     t.visibility = 'visible' 
     AND t.create_time >= '2023-12-14 00:00:00'  
     AND t.create_time <= '2024-02-15 18:00:00'
          
        LIMIT 30000
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(rows[0])
    print("Total rows are:  ", len(rows))

    fields = ['Дата поступления','Время поступления', 'Способ подачи обращения', 'Номер обращения', 'Заявитель (фамилия и инициалы)',
              'Название субъекта РФ', 'Номер СТД (КСА)', 'Текст обращения', 'Классификация обращения', 'Приоритет обращения',
              'Наименование подсистемы/компонента', 'Исполнитель обращения (фамилия и инициалы)', 'Текущий статус',
              'Описание оказанной консультации или решения по обращению', 'Необходимость модификации СПО (да/нет)',
              'Номер листа внимания', 'дата закрытия', 'Время закрытия', 'Общее время обработки', 'Инициатор (фамилия и инициалы)',
              'Компания инициатора', 'Массовый инцидент', 'tid', 'service_id', 'ticket_state_id', 'create_time', 'exec_time',
              'status', 'service', 'queue', 'SLA norm', 'SLA fact', 'время: Зарегистрирована', 'время: В работе', 'время: Отложенное исполнение',
              'время: Ожидание клиента', 'время: На согласовании', 'visibility', 'region']

    fields2 =['Статус', 'Количество']

    df = pd.DataFrame(list(rows), columns=fields)
    #df = pd.DataFrame(list(rows))
    df['Дата поступления'] = pd.to_datetime(df['Дата поступления'], format='%d.%m.%Y').dt.date
    df['Текст обращения'] = df['Текст обращения'].str.replace('\n', ' ')
    df['Описание оказанной консультации или решения по обращению'] = df['Описание оказанной консультации или решения по обращению'].str.replace('\n', ' ')

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
            df.index += 1
            df.to_excel(writer, sheet_name='Заявки', index=True, index_label='№ п/п')
            workbook = writer.book
            worksheet = writer.sheets['Заявки']
            worksheet.autofit()
            worksheet.freeze_panes(1, 0)
            for i, height in enumerate([25] * df.shape[0]):  # устанавливаем высоту строк
                worksheet.set_row(i, height)

            worksheet.autofilter(0, 1, len(df), len(df.columns))
            workbook.close()
        else:
            services = []
            iterservices = topic.services.all()
            for item in iterservices:
                services.append(item.name)
            servis_df = df.loc[df['Наименование подсистемы/компонента'].isin(services)]
            print(servis_df)
            print(len(servis_df.columns))
            print(len(servis_df))
            counts = servis_df.groupby('Наименование подсистемы/компонента')['Текущий статус'].value_counts().to_frame(name='Всего')
            #servis_df['Дата поступления'] = pd.to_datetime(servis_df['Дата поступления'], format='%d.%m.%Y')
            today = datetime.datetime.now().date()
            five_days_ago = today - datetime.timedelta(days=5)
            ten_days_ago = today - datetime.timedelta(days=10)
            filtered_df = servis_df[df['Дата поступления'] < five_days_ago]
            filtered_df_10 = servis_df[df['Дата поступления'] < ten_days_ago]
            filtered_counts = filtered_df.groupby('Наименование подсистемы/компонента')['Текущий статус'].value_counts().to_frame()
            filtered_counts_10 = filtered_df_10.groupby('Наименование подсистемы/компонента')['Текущий статус'].value_counts().to_frame()
            print(counts)
            counts['5 дней'] = filtered_counts
            counts['10 дней'] = filtered_counts_10
            print(counts)
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            servis_df.index += 1
            servis_df.to_excel(writer, sheet_name='Заявки', index=True, index_label='№ п/п')
            counts.to_excel(writer, sheet_name='Статистика')
            workbook = writer.book
            worksheet = writer.sheets['Заявки']
            worksheet.autofit()
            worksheet.freeze_panes(1, 0)
            for i, height in enumerate([25] * servis_df.shape[0]):  # устанавливаем высоту строк
                worksheet.set_row(i, height)

            worksheet.autofilter(0, 1, len(servis_df), len(servis_df.columns))
            worksheet2 = writer.sheets['Статистика']
            worksheet2.autofit()
            workbook.close()



        emails = []
        iteremails = topic.recivers.all()
        print(iteremails[0])
        for email in iteremails:
            emails.append(email.email)
        print(emails)
        print(filename)

        #send_otchet_email_task.delay(emails, subject, 'post@cifro.tech', message, filename)

        dropfields = ['Инициатор (фамилия и инициалы)',
              'Компания инициатора', 'Массовый инцидент', 'tid', 'service_id', 'ticket_state_id', 'create_time', 'exec_time',
              'status', 'service', 'queue', 'SLA norm', 'SLA fact', 'время: Зарегистрирована', 'время: В работе', 'время: Отложенное исполнение',
              'время: Ожидание клиента', 'время: На согласовании', 'visibility']

        df_to_fci = df.drop(columns=dropfields)
        print(df_to_fci.head())

        fcitopics = FciTopic.objects.all()
        print(fcitopics)
        for fcitopic in fcitopics:

            filename = f"Журнал обращений пользователей {fcitopic.name} на {datetime.date.today().isoformat()}.xlsx"
            subject = f"ЦП.Журнал обращений пользователей {fcitopic.name} на {datetime.date.today().isoformat()}"
            path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
            if fcitopic.slug == 'all':
                print(df_to_fci)
                print(len(df_to_fci.columns))
                print(len(df_to_fci))
                writer = pd.ExcelWriter(path, engine='xlsxwriter')
                df_to_fci.index += 1
                df_to_fci.to_excel(writer, sheet_name='Обращения', index=True, index_label='№ п/п')
                workbook = writer.book
                worksheet = writer.sheets['Обращения']
                worksheet.autofit()
                worksheet.freeze_panes(1, 0)
                for i, height in enumerate([25] * df.shape[0]):  # устанавливаем высоту строк
                    worksheet.set_row(i, height)

                worksheet.autofilter(0, 1, len(df_to_fci), len(df_to_fci.columns))
                workbook.close()
            elif fcitopic.slug == 'region':
                writer = pd.ExcelWriter(path, engine='xlsxwriter')
                workbook = writer.book
                for i in range(00, 96):
                    # if i < 10:
                    #     r_number = f'0{i}'
                    # else:
                    #     r_number = f'{i}'
                    r_number = f'{i}'
                    print(r_number)
                    fci_servis_df_region = df_to_fci.query(f"region == {r_number}")
                    fci_servis_df_region.index += 1
                    fci_servis_df_region_execl = fci_servis_df_region.drop(columns=['region'])
                    fci_servis_df_region_execl.to_excel(writer, sheet_name=r_number, index=True, index_label='№ п/п')
                    worksheet = writer.sheets[r_number]
                    worksheet.autofit()
                    worksheet.freeze_panes(1, 0)
                    for i, height in enumerate([25] * fci_servis_df_region_execl.shape[0]):  # устанавливаем высоту строк
                        worksheet.set_row(i, height)

                    worksheet.autofilter(0, 1, len(fci_servis_df_region_execl), len(fci_servis_df_region_execl.columns))

                workbook.close()


            else:
                fciservices = []
                fciiterservices = fcitopic.services.all()
                for item in fciiterservices:
                    fciservices.append(item.name)
                fci_servis_df = df_to_fci.loc[df['Наименование подсистемы/компонента'].isin(fciservices)]
                print(fci_servis_df)
                print(len(fci_servis_df.columns))
                print(len(fci_servis_df))
                writer = pd.ExcelWriter(path, engine='xlsxwriter')
                fci_servis_df.index += 1
                fci_servis_df.to_excel(writer, sheet_name='Обращения', index=True, index_label='№ п/п')
                workbook = writer.book
                worksheet = writer.sheets['Обращения']
                worksheet.autofit()
                worksheet.freeze_panes(1, 0)
                for i, height in enumerate([25] * fci_servis_df.shape[0]):  # устанавливаем высоту строк
                    worksheet.set_row(i, height)

                worksheet.autofilter(0, 1, len(fci_servis_df), len(fci_servis_df.columns))

                workbook.close()

            emails = []
            fciiteremails = fcitopic.fcirecivers.all()
            iiteremails = fcitopic.recivers.all()
            print(iteremails[0])
            for email in fciiteremails:
                emails.append(email.email)
            for email in iiteremails:
                emails.append(email.email)
            print(emails)
            print(filename)

            send_otchet_email_task.delay(emails, subject, 'post@cifro.tech', message, filename)


def todb():

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

    date = datetime.date.today()
    time = datetime.time(18, 00)
    date_for_otchet = datetime.datetime.combine(date, time)
    date_for_otchet2 = f"'{date_for_otchet}'"

    print(date)
    print(date_for_otchet)
    print(date_for_otchet2)
    cursor = connect.cursor()
    sql = f"""
        SELECT  
         *  

        FROM  
         report.v_try_source t 

        WHERE  
         t.tid > 0 
         AND t.create_time >= '2023-05-16 00:00:00' 

        LIMIT 30000
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(rows[0])
    print("Total rows are:  ", len(rows))

    fields = [
        'Дата поступления', 'Время поступления', 'Номер обращения', 'Массовый инцидент',
        'Заявитель(фамилия и инициалы)',
        'Название субъекта РФ', 'Инициатор (фамилия и инициалы)', 'Компания инициатора', 'Номер СТД(КСА)',
        'Текст обращения', 'Классификация обращения', 'Приоритет обращения', 'Наименование подсистемы',
        'Исполнитель обращения',
        'Текущий статус', 'Описание оказанной консультации', 'Необходимость модификации СПО', 'Номер листа внимания',
        'дата закрытия', 'Время закрытия', 'Общее время обработки', 'Канал поступления', 'tid', 'service_id',
        'ticket_state_id',
        'create_time', 'exec_time', 'status', 'service', 'queue', 'SLA_norm', 'SLA_fact', 'время: Зарегистрирована',
        'время: В работе', 'время: Отложенное исполнение', 'время: Ожидание клиента', 'время: На согласовании',
        'visibility'
    ]
    #ro = ('12.02.2024', '18:06:51', '2024021200023', None, 'Никишенко С.В.', 'Республика Крым (91)', '', '', '91T015', 'Компонент: Компонент «Работа с базой данных»,\nДобрый день! При работе с инцидентами в меню РУИП, при загрузке файлов, нет\nдоступа к НСИ либо плачущий смайлик\nОбрабатываю инциденты\n', 'Инцидент', 'Низкий', 'НСИ', None, 'в работе', 'В процессе обработки обращения не было оставлено комментариев', None, '', '', '', '00:00:00', 'Портал', 27837, 7, 4, datetime.datetime(2024, 2, 12, 18, 6, 51), None, 'В работе', 'СПО НСИ Инцидент', '2-я линия техподдержки СПО НСИ', '48:00:00', '00:00:00', '00:00:00', '00:00:00', None, None, None, 'visible')
    #array = []
    #array.append(ro)
    df = pd.DataFrame(list(rows), columns=fields)
    host = os.getenv("DB_HOST")
    username = os.getenv("DB_USER")
    password2 = os.getenv("DB_PASSWORD")
    dbname = os.getenv("DB_NAME_TIKETS")
    port2 = os.getenv("DB_PORT")
    sqlstring = f'postgresql://{username}:{password2}@{host}:{port2}/{dbname}'
    print(sqlstring)
    #df = pd.DataFrame(ro)
    engine = create_engine(sqlstring)
    print(df.head())
    df.to_sql('tickets', con=engine, if_exists='replace', index=False)


