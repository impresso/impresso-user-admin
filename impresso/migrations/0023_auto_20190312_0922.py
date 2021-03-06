# Generated by Django 2.1.5 on 2019-03-12 09:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('impresso', '0022_auto_20190309_1552'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attachment',
            name='id',
        ),
        migrations.AddField(
            model_name='attachment',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='impresso.Collection'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='search_query',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='impresso.SearchQuery'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='job',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='impresso.Job'),
        ),
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(choices=[('REA', 'ready'), ('RUN', 'running'), ('DON', 'Finished, no errors!'), ('ARC', 'Finished, archived by the user'), ('STO', 'Please stop'), ('ERR', 'Ops, errors!')], default='REA', max_length=3),
        ),
        migrations.AlterField(
            model_name='searchquery',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='searchquery',
            name='name',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
