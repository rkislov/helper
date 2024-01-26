import psycopg2
from django.core.management.base import BaseCommand
from mail.models import Region
from mail.utils import generate_fullotchet


class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        generate_fullotchet()
        # regions = Region.objects.filter(build_otchet=True)
        #
        # for region in regions:
        #     generate_otchet(region)
