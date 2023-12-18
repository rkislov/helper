import psycopg2
from django.core.management.base import BaseCommand
from mail.models import Region
from mail.utils import generate_otchet


class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):

        regions = Region.objects.all()

        for region in regions:
            generate_otchet(region)
