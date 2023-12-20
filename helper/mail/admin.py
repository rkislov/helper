from django.contrib import admin
from .models import Region


admin.site.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'region_number', 'region_admin_email', 'build_otchet']
    search_fields = ['id', 'region_number', 'region_admin_email']
    list_filter = ['build_otchet']


    def match_update(self, request, *args):
        from django.core.management import call_command
        call_command("otchet")