from django.core.mail import EmailMessage
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
import os
from django.conf import settings as django_settings
import magic

logger = get_task_logger(__name__)



@shared_task
def check_email():
    call_command("mailcheck", )


@shared_task()
def send_otchet_email_task(email_address, subject, from_email, message, filename):
    with open(os.path.join(django_settings.STATIC_ROOT, f"{filename}"), 'rb') as file:
        file_content = file.read()

    mime_type = magic.from_buffer(file_content, mime=True)
    """Sends an email when the feedback form has been submitted."""
    file_name = os.path.basename(filename)
    email = EmailMessage(subject, message, from_email, email_address)
    EmailMessage(
        {subject},
        {message},
        {from_email},
        list(email_address),
    )
    email.attach(file_name, file_content, mime_type)
    email.send()