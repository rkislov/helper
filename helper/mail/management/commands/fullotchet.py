from django.core.management.base import BaseCommand
from mail.utils import create_fullotchet

from helper.mail.models import Topic


class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        topics = Topic.objects.all()

        for topic in topics:
            create_fullotchet(topic)
        # regions = Region.objects.filter(build_otchet=True)
        #
        # for region in regions:
        #     generate_otchet(region)
