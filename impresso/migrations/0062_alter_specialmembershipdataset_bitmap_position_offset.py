from django.db import migrations

# Freeze this value in the migration to avoid future model-constant drift.
BITMAP_PLAN_OFFSET = 5


def _shift_bitmap_positions(apps, schema_editor, delta: int, descending: bool) -> None:
    connection = schema_editor.connection

    if connection.vendor == "mysql":
        order = "DESC" if descending else "ASC"
        with connection.cursor() as cursor:
            cursor.execute("SET SQL_SAFE_UPDATES = 0")
            try:
                cursor.execute(
                    f"""
                    UPDATE impresso_datasetbitmapposition
                    SET bitmap_position = bitmap_position + %s
                    ORDER BY bitmap_position {order}
                    """,
                    [delta],
                )
            finally:
                cursor.execute("SET SQL_SAFE_UPDATES = 1")
        return

    # SQLite and other backends: shift row-by-row in a safe order to avoid unique collisions.
    SpecialMembershipDataset = apps.get_model("impresso", "SpecialMembershipDataset")
    db_alias = connection.alias
    ordering = "-bitmap_position" if descending else "bitmap_position"

    rows = (
        SpecialMembershipDataset.objects.using(db_alias)
        .order_by(ordering)
        .values_list("pk", "bitmap_position")
    )
    for pk, bitmap_position in rows.iterator():
        SpecialMembershipDataset.objects.using(db_alias).filter(pk=pk).update(
            bitmap_position=bitmap_position + delta
        )


def offset_bitmap_position(apps, schema_editor) -> None:
    _shift_bitmap_positions(
        apps=apps,
        schema_editor=schema_editor,
        delta=BITMAP_PLAN_OFFSET,
        descending=True,
    )


def reverse(apps, schema_editor) -> None:
    _shift_bitmap_positions(
        apps=apps,
        schema_editor=schema_editor,
        delta=-BITMAP_PLAN_OFFSET,
        descending=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("impresso", "0061_alter_specialmembershipdataset_bitmap_position_and_more"),
    ]

    operations = [
        migrations.RunPython(offset_bitmap_position, reverse),
    ]
