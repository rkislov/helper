import os

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
import imaplib
import email
from email.header import decode_header
import requests
import datetime
from dotenv import load_dotenv
load_dotenv()
#from helper.helper.celery import app


#@app.task
class Command(BaseCommand):
    help = "Загружает почту из ящика и сохраняет в cloud"

    def handle(self, *args, **kwargs):

        imap_server = os.getenv("EMAIL_HOST")
        username = os.getenv("EMAIL_HOST_USER")
        password = os.getenv("EMAIL_HOST_PASSWORD")

        # Параметры Nextcloud Deck
        nextcloud_url = os.getenv("NEXTCLOUD_URL")
        nextcloud_username = os.getenv("NEXTCLOUD_USER ")
        nextcloud_password = os.getenv("NEXTCLOUD_PASSWORD ")

        # Подключение к почтовому серверу
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select('INBOX')

        # Поиск писем
        status, data = mail.search(None, 'UNSEEN')
        message_ids = data[0].split()

        if len(message_ids) > 0:
            print(f"Найдено {len(message_ids)} писем:")
            for message_id in message_ids:
                # Получение данных письма
                status, message_data = mail.fetch(message_id, '(RFC822)')
                email_data = message_data[0][1]
                email_message = email.message_from_bytes(email_data)
                subject = email_message["Subject"]
                subject_list = decode_header(email_message["Subject"])
                sub_list = []
                for subj in subject_list:
                    if subj[1]:
                        subj = (subj[0].decode(subj[1]))
                    elif type(subj[0]) == bytes:
                        subj = subj[0].decode('utf-8')
                    else:
                        subj = subj[0]
                    sub_list.append(subj)

                subjects = ''.join(sub_list)

                with open("num.txt", "r") as file:
                    number = int(file.read())
                # Вывод числа
                print("Число из файла:", number)
                d = datetime.datetime.now()
                full_name = f"{number}-{d.month}.{d.year}"
                print(full_name)
                # Увеличение числа на 1
                number += 1
                # Запись увеличенного числа в файл
                with open("num.txt", "w") as file:
                    file.write(str(number))

                session = requests.Session()
                session.headers.update({
                    'OCS-APIRequest': 'true',
                    'Content-Type': 'application/json'
                })
                session.auth = (nextcloud_username, nextcloud_password)

                attachments = []
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type in ['application/pdf', 'image/jpeg']:
                        attachment = part.get_payload(decode=True)
                        filename = part.get_filename()
                        filename_list = decode_header(filename)
                        fn_list = []
                        for filen in filename_list:
                            if filen[1]:
                                filen = (filen[0].decode(filen[1]))
                            elif type(filen[0]) == bytes:
                                filen = filen[0].decode('utf-8')
                            else:
                                filen = filen[0]
                            fn_list.append(filen)
                        filenames = ''.join(fn_list)
                        filenm = (f"Вх № {full_name} от {d.day}.{d.month}.{d.year} - {filenames}")
                        full_subj = (f"Вх № {full_name} от {d.day}.{d.month}.{d.year} - {subjects}")
                        attachments.append((filenm, attachment))

                        for filenm, attachment in attachments:
                            files = [
                                ('file', (filenm, attachment, 'application/octet-stream'))
                            ]

                            # Обработка для каждого письма
                            # Создание новой карточки в Nextcloud Deck
                            response = session.post(
                                f"{nextcloud_url}/apps/deck/api/v1.0/boards/54/stacks/139/cards",
                                json={
                                    'title': full_subj,
                                    "type": "plain",
                                    "order": 999,
                                    "duedate": None,
                                },
                            )

                            card_data = response.json()
                            card_id = card_data['id']

                            if response.status_code == 200:
                                print(f"Создана новая карточка с ID: {card_id}")
                            else:
                                print("Ошибка при создании карточки в Nextcloud Deck", response.status_code)
                            session1 = requests.Session()
                            # session1.headers.update({
                            # 'OCS-APIRequest': 'true',
                            # 'Content-Type': 'mapplication/json',
                            # })
                            session1.auth = (nextcloud_username, nextcloud_password)
                            payload = {'type': 'file'}
                            attachment_response = session1.post(
                                f"{nextcloud_url}/apps/deck/api/v1.0/boards/54/stacks/139/cards/{card_id}/attachments",
                                data=payload,
                                files=files
                            )
                            if attachment_response.status_code == 200:
                                print(f"вложение {filenm} к карточке с ID: {card_id} подгружено")
                                sender = email.utils.parseaddr(email_message['From'])[1]
                                recipients = [addr[1] for addr in
                                              email.utils.getaddresses(email_message.get_all('CC', []))]
                                send_mail(
                                    f"{subject}",
                                    f"Ваше письмо зарегистрировано {full_subj}",
                                    "post@cifro.tech",
                                    [sender],
                                    fail_silently=False,
                                )
                                msg = ''''\
                                From: ${username}
                                To: ${sender}
                                Subject: Письмо зарегистрировано

                                '''
                                # reply_message = f"ваше письмо успешно зарегистрировано ${full_subj}"
                                # ascii_reply_message = reply_message.encode('utf-8')
                                # ascii_msg = msg.encode('utf-8')
                                # # Отправка ответа
                                # smtp_server = smtplib.SMTP(smtp_server)
                                # smtp_server.starttls()
                                # smtp_server.login(username, password)
                                # smtp_server.sendmail(username, [sender] + recipients, ascii_msg)
                                # smtp_server.quit()

                                mail.store(message_id, '+FLAGS', '\\Seen')
                            else:
                                print(
                                    f"Ошибка при подгрузке вложения к карточке {card_id} в Nextcloud Deck {attachment_response.status_code} {attachment_response.text}")
                                # Отметить письмо как прочитанное
                    mail.store(message_id, '+FLAGS', '\\Seen')
        else:
            print("Писем не найдено")

        # Закрытие соединения
        mail.close()
        mail.logout()