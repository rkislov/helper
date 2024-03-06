from django.core.management.base import BaseCommand
from mail.utils import create_fullotchet_podryad




class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):
        create_fullotchet_podryad()
        # regions = Region.objects.filter(build_otchet=True)
        #
        # for region in regions:
        #     generate_otchet(region)
