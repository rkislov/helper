from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.core.management import call_command
from django.urls import path
from .models import Region


class RegionAdmin(admin.ModelAdmin):
    change_list_template = "region_changelist.html"
    list_display = ['id', 'region_number', 'region_admin_email', 'build_otchet']
    search_fields = ['id', 'region_number', 'region_admin_email']

    list_filter = ['build_otchet']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('otchet/', self.send_otchet),
        ]
        return my_urls + urls
    def send_otchet(self, request):
        call_command("otchet")
        self.message_user(request, "Отчет отправлен")
        return HttpResponseRedirect("../")


admin.site.register(Region, RegionAdmin)