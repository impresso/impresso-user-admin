from django.db import migrations, models
from django.db.models import Max


def backfill_null_bitmap_positions(apps, _schema_editor):
    SpecialMembershipDataset = apps.get_model("impresso", "SpecialMembershipDataset")

    # Lock in read-consistent max first, then assign sequentially to nulls
    max_position = SpecialMembershipDataset.objects.aggregate(Max("bitmap_position"))[
        "bitmap_position__max"
    ]
    next_position = 0 if max_position is None else max_position + 1

    null_rows = SpecialMembershipDataset.objects.filter(
        bitmap_position__isnull=True
    ).order_by("id")

    for row in null_rows:
        row.bitmap_position = next_position
        row.save(update_fields=["bitmap_position"])
        next_position += 1


def reverse_noop(apps, schema_editor):
    # No safe reverse — we don't know which rows were originally null.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("impresso", "0060_baristaconversation"),
    ]

    operations = [
        migrations.RunPython(backfill_null_bitmap_positions, reverse_noop),
        migrations.AlterField(
            model_name="specialmembershipdataset",
            name="bitmap_position",
            field=models.PositiveIntegerField(default=0, unique=True),
        ),
        migrations.AlterField(
            model_name="userspecialmembershiprequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("pending-t", "Pending (Temporary)"),
                    ("approved", "Approved"),
                    ("temporary", "Approved (Temporary)"),
                    ("rejected", "Rejected"),
                    ("revoked", "Revoked"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
    ]
