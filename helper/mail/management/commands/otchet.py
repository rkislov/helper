import psycopg2
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings as django_settings
import os
import csv
import datetime
from mail.models import Region
from mail.utils import generate_otchet


class Command(BaseCommand):
    help = "проверят наличие новых заявок в ОТРС"

    def handle(self, *args, **kwargs):

        regions = Region.objects.all()

        for region in regions:
            generate_otchet(region)
