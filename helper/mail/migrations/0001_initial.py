# Generated by Django 4.2.8 on 2023-12-18 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Regadmins',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region_number', models.CharField(max_length=2)),
                ('email', models.EmailField(max_length=254)),
                ('build_otchet', models.BooleanField(default=False)),
            ],
        ),
    ]
