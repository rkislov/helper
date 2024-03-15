from django.core.management.base import BaseCommand
from mail.utils import test_index




class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        test_index()
        # regions = Region.objects.filter(build_otchet=True)
        #
        # for region in regions:
        #     generate_otchet(region)
