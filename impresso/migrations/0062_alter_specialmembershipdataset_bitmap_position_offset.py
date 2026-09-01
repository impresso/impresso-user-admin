from django.db import migrations, connection
from impresso.models import UserBitmap


def offset_bitmap_position(apps, schema_editor):
    with connection.cursor() as cursor:
        # process highest values first to avoid unique constraint collisions
        cursor.execute("SET SQL_SAFE_UPDATES = 0")
        cursor.execute(f"""
            UPDATE impresso_datasetbitmapposition
            SET bitmap_position = bitmap_position + {UserBitmap.BITMAP_PLAN_MAX_LENGTH}
            ORDER BY bitmap_position DESC
        """)
        cursor.execute("SET SQL_SAFE_UPDATES = 1")


def reverse(apps, schema_editor):
    with connection.cursor() as cursor:
        # process lowest values first to avoid unique constraint collisions
        cursor.execute("SET SQL_SAFE_UPDATES = 0")
        cursor.execute(f"""
            UPDATE impresso_datasetbitmapposition
            SET bitmap_position = bitmap_position - {UserBitmap.BITMAP_PLAN_MAX_LENGTH}
            ORDER BY bitmap_position ASC
        """)
        cursor.execute("SET SQL_SAFE_UPDATES = 1")


class Migration(migrations.Migration):
    dependencies = [
        ("impresso", "0061_alter_specialmembershipdataset_bitmap_position_and_more"),
    ]
    operations = [
        migrations.RunPython(offset_bitmap_position, reverse),
    ]
