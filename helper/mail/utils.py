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


def generate_newotchet():
   # region = Region.objects.filter(region_number=region_number).first()

    connect = psycopg2.connect(host=os.getenv("DBE_HOST"), user=os.getenv("DBE_USER"),
                               password=os.getenv("DBE_PASSWORD"), dbname=os.getenv("DBE_NAME"),
                               port=os.getenv("DBE_PORT"))

#     filename = f"region-{region_number}-{datetime.date.today().isoformat()}.xlsx"
#     subject = f"region-{region_number}-{datetime.date.today().isoformat()}"
#     message = f"""Добрый день.
#
# Во вложении отчет по заявкам по региону №{region_number}  на {datetime.date.today().isoformat()}
#
#
# Служба поддержки ЦП
# Телефон: 8-800-301-23-39
# E-mail:  supportcp@cloud.rt.ru
#     """
#     fields = ['Номер заявки', 'Тема заявки', 'ИКСРФ/ТИК', 'ФИО Заявителя', 'email заявителя', 'Дата', 'Статус',
#               'линия ТП', 'Комментарий']
#     search_region = f"'%{region.region_number}%'"
#     print(search_region)

    cursor = connect.cursor()
    sql = f"""
   with abc as (
select fa.a_body, fa.id, fa.ticket_id , ROW_NUMBER ()
OVER ( PARTITION BY fa.ticket_id ORDER BY fa.id) || '. ' || fa.a_body comm, a.is_visible_for_customer
from 
report.v_fact_article fa
join public.article a on a.id = fa.id and a.ticket_id = fa.ticket_id 
where fa.article_sender_type in ('agent')
and fa."article_type" in ('AgentNote','Decision')
and a.is_visible_for_customer = 1
and fa.id != 17072
order by fa.ticket_id  )

SELECT

t.id,
ROW_NUMBER ()  OVER ( ORDER BY t.create_time DESC) AS "№№ п/п", 
t.create_time::date as "Дата поступления", 
to_char(t.create_time, 'hh24:mm:ss') as "Время поступления",
t.tn AS "Номер обращения",
c.last_name || ' ' ||c.first_name ||' '|| c.middle_name AS "Заявитель (фамилия и инициалы)",
c.lvl2 AS "Название субъекта РФ",

case when split_part(reverse(split_part(reverse(c.lvl3), ' ', 1)), '"', 1) in ('Липецка', 'комиссия', 'области', 'района') then ''
else split_part(reverse(split_part(reverse(c.lvl3), ' ', 1)), '"', 1) end AS "Номер СТД (КСА)",

case WHEN t.initialnote IS NULL OR (LENGTH(initialnote)<150 AND (
(lower(t.initialnote) ~'^[\t\n\v\f\r \u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000]*-{2}.*mail.ru$' 
AND (lower(initialnote) !~~*'%пересланное%' OR lower(initialnote) !~~*'%пересылаемое%' ))
OR (lower(t.initialnote) ~'^[\t\n\v\f\r \u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000]*-{2}.*mail.ru для android$' 
AND (lower(initialnote) !~~*'%пересланное%' OR lower(initialnote) !~~*'%пересылаемое%' ))
OR lower(initialnote) ~'^[\t\n\v\f\r \u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000]*-{2}(\s|\S)'
OR lower(t.initialnote) ~'^[\t\n\v\f\r \u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000]*$' 
OR lower(t.initialnote) ~'^(?=с уважением)|(?=c уважением,])\s{1}.*'
OR lower(t.initialnote) ~'^[\t\n\v\f\r \u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000]*(?=с уважением)|(?=c уважением,).*'
OR t.initialnote IN ('',E'\n','.','-','й') 
OR lower(t.initialnote) like lower('%no text message%')))
THEN 'Информация по обращению во вложении'|| '. ' ||t.title ELSE left(t.initialnote,4000) end AS "Текст обращения",

tt.name AS "Классификация обращения",
tp.name AS "Приоритет обращения",
s.name AS "Наименование подсистемы/компонента",
u.last_name || ' ' || u.first_name ||' '|| u.middle_name AS "Исполнитель обращения (фамилия и инициалы)",
ts.rus_name AS "Текущий статус",

CASE WHEN t.tn = '2023112200246' THEN 'Пункт г) реализован в рамках релиза 2.2.1, зафиксирован в  ВР.ПАИП.КИФ.003 в п.8. Продемонстрировано функциональному заказчику в рамках ПСИ. Остальные пункты отклонены по согласованию с функциональным заказчиком.'
WHEN t.tn = '2023112200248' THEN 'Реализовано в рамках релиза  2.2.1, зафиксировано в  ВР.ПАИП.КИФ.003 в п.10. Продемонстрировано функциональному заказчику в рамках ПСИ.'
WHEN t.tn = '2023112200255' THEN 'Реализовано в рамках релиза 2.2.1, зафиксировано в  ВР.ПАИП.КИФ.003 в п.9. Продемонстрировано функциональному заказчику в рамках ПСИ.'
ELSE coalesce(coalesce(cc.Комментарии,t.decision),'В процессе обработки обращения не было оставлено комментариев')
END AS "Описание оказанной консультации или решения по обращению",

dfv.value_text AS "Необходимость модификации СПО (да/нет)",
'' AS "Номер листа внимания",
t.exec_time::date AS "дата закрытия", 
to_char(t.exec_time, 'hh24:mm:ss') AS "Время закрытия",
TO_CHAR(wt.s * '1 second'::INTERVAL, 'HH24:MI') AS "Общее время обработки"



FROM 

report.v_fact_ticket t
left join public.dynamic_field_value d on d.object_id = t.id and d.field_id=1055
left join public.dynamic_field_value df on df.object_id = t.id and df.field_id=1054
left join public.dynamic_field_value dfv on dfv.object_id = t.id and dfv.field_id=1053
left join lateral (select name, id from report.v_dim_priority where id = t.ticket_priority_id ) tp on  true 
left join report.v_dim_ticket_type tt on t.type_id = tt.id 
left join report.v_dim_ticket_state ts on ts.id= t.ticket_state_id 
left join report.v_dim_service s on s.id= t.service_id 
left join report.v_dim_queue q on t.queue_id = q.id
left join report.v_dim_client c on lower(c.login) = lower(t.customer_user_id) 
left join report.v_dim_user u on u.id= t.user_id and t.user_id != 1 
left join report.v_dim_client uc on u.client_id = uc.id 
left join (
	select  ticket_id, STRING_AGG(t.comm, E'\n') as Комментарии from abc t
	group by ticket_id
) cc on cc.ticket_id = t.id
LEFT JOIN LATERAL (SELECT SUM(working_time) AS s FROM report.v_fact_ticket_time tt WHERE tt.ticket_id = t.id) wt ON TRUE

where 

t.tn IN ('2023062800130','2023062800129','2023080800040','2023080700034','2023080800041','2023080800042','2023080800043','2023080800044','2023080700036','2023080800045','2023080700037','2023080800046','2023080800047','2023080800048','2023080800049','2023080800050')
OR (
	(c.full_path not LIKE '%Ростелеком%' and  c.lvl2 is not null)
	and (t.create_time::date >= '2024-01-22')
	and (t.create_time::date <= '2024-01-30' )
	and (s.name != 'Приёмка СПО ПАИП')
	and (c.last_name != 'Тестовая' and c.last_name != 'Тестовый')
)
"""
    cursor.execute(sql)
    rows = cursor.fetchall()
    print("Total rows are:  ", len(rows))
    print("Row 0: ", rows[0])
    # path = os.path.relpath(os.path.join(django_settings.STATIC_ROOT, f'{filename}'))
    # workbook = xlsxwriter.Workbook(path)
    # worksheet = workbook.add_worksheet()
    # format1 = workbook.add_format({'bg_color': '#D9D9D9', 'bold': True})
    # row = 0
    # col = 0
    # for f in fields:
    #     worksheet.write(row, col, f, format1)
    #     col += 1
    # row += 1
    # col = 0
    # for ro in rows:
    #     date_time = f"{ro[5]}"
    #     worksheet.write(row, col, ro[0])
    #     worksheet.write(row, col + 1, ro[1])
    #     worksheet.write(row, col + 2, ro[2])
    #     worksheet.write(row, col + 3, ro[3])
    #     worksheet.write(row, col + 4, ro[4])
    #     worksheet.write(row, col + 5, date_time)
    #     worksheet.write(row, col + 6, ro[6])
    #     worksheet.write(row, col + 7, ro[7])
    #     if ro[8] != None:
    #         worksheet.write(row, col + 8, ro[8].strip())
    #     row += 1
    #     col = 0
    # worksheet.autofit()
    # worksheet.freeze_panes(1, 0)
    # worksheet.autofilter(0, 0, 1000, 8)
    # # worksheet.set_default_row(50)
    # workbook.close()
    # send_otchet_email_task.delay([region.region_admin_email], subject, 'post@cifro.tech', message, filename)
