# Generated by Django 5.1.4 on 2024-12-20 16:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0052_delete_userrequestingchangeplan'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='userchangeplanrequest',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='changePlanRequest', to=settings.AUTH_USER_MODEL),
        ),
    ]
