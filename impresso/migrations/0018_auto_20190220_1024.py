# Generated by Django 2.1.5 on 2019-02-20 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0017_collectableitem_item_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collectableitem',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
