# Generated by Django 5.0.7 on 2024-08-06 09:36

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0036_searchquery_hash_alter_job_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetBitmapPosition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('bitmap_position', models.PositiveIntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserBitmap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bitmap', models.BinaryField()),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bitmap', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Bitmap',
                'verbose_name_plural': 'User Bitmaps',
            },
        ),
    ]
