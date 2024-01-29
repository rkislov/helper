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


class Service(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"


    def __str__(self):
        return self.name


class Reciver(models.Model):
    email = models.EmailField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"


    def __str__(self):
        return self.email


class Topic(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    services = models.ManyToManyField(Service, related_name="topics")
    recivers = models.ManyToManyField(Reciver, related_name="topics", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

    def __str__(self):
        return self.name