from django.db import models


class Region(models.Model):
    region_number = models.CharField(max_length=2)
    region_admin_email = models.EmailField()
    build_otchet = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

    def __str__(self):
        return self.region_number