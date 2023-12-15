#from django.core.mail import send_mail
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)

# @shared_task()
# def send_email_task(email_address, subject, message):
#     """Sends an email when the feedback form has been submitted."""
#     # Simulate expensive operation(s) that freeze Django
#     send_mail(
#         f"{subject}",
#         f"\t{message}\n\nThank you!",
#         "post@cifro.tech",
#         [email_address],
#         fail_silently=False,
#     )


@shared_task
def check_email():
    call_command("mailcheck", )
