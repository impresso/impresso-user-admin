# Generated by Django 3.0.7 on 2020-11-01 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0033_auto_20201028_0816'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectableitem',
            name='search_query_score',
            field=models.FloatField(db_index=True, default=0.0),
        ),
    ]
