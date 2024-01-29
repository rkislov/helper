from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.core.management import call_command
from django.urls import path
from .models import Region, Reciver, Service, Topic


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


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    prepopulated_fields = {"slug": ("name",)}


class ReciverAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'description']
    search_fields = ['id', 'email', 'description']


class TopicAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    search_fields = ['id', 'name', 'slug']


admin.site.register(Region, RegionAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Reciver, ReciverAdmin)
admin.site.register(Topic, TopicAdmin)