from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from impresso.tasks import update_user_bitmap_task


class Command(BaseCommand):
    help = "Update user bitmap using celery task"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("bitmap", type=str, nargs="?", default=None)

    def handle(self, username, *args, **options):
        self.stdout.write(f"Get user with username: {username}")
        user = User.objects.get(username=username)
        self.stdout.write(f"User: pk={user.id} \033[34m{user.username}\033[0m")
        # currrent user bitmap
        user_current_bitmap = user.bitmap.bitmap
        user_current_bitmap_as_bigint = int.from_bytes(
            user_current_bitmap, byteorder="big"
        )
        self.stdout.write(
            f"user SAVED bitmap():\n  \033[34m{bin(user_current_bitmap_as_bigint)}\033[0m"
        )
        user_expected_bitmap = user.bitmap.get_up_to_date_bitmap()

        self.stdout.write(
            f"user EXPECTED get_up_to_date_bitmap():\n  \033[34m{bin(user_expected_bitmap)}\033[0m"
        )
        difference = user_current_bitmap_as_bigint ^ user_expected_bitmap
        self.stdout.write(
            f"SAVED ^ EXPECTED difference:\n  \033[34m{bin(difference)}\033[0m"
        )

        # collection_id, user_id, items_ids_to_add=[], items_ids_to_remove=[]
        message = update_user_bitmap_task.delay(
            collection_id=collection.id,
            user_id=user.id,
            items_ids_to_add=items_to_add,
            items_ids_to_remove=items_to_remove,
        )
        self.stdout.write(
            f"\n5. Task \033[36m{message.id}\033[0m launched, check celery."
        )
