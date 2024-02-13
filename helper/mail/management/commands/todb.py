from django.core.management.base import BaseCommand
from mail.utils import todb




class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        todb()
        # regions = Region.objects.filter(build_otchet=True)
        #
        # for region in regions:
        #     generate_otchet(region)
