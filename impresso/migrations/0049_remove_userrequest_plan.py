# Generated by Django 5.0.8 on 2024-11-25 07:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0048_userrequest_plan_alter_job_extra_alter_job_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userrequest',
            name='plan',
        ),
    ]
