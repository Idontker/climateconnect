# Generated by Django 2.2.13 on 2020-11-17 17:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('climateconnect_api', '0039_auto_20201117_1723'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='email_updates_on_projects',
        ),
    ]
