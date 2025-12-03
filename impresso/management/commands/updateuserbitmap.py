from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from impresso.tasks import update_user_bitmap_task
from impresso.utils.bitmask import BitMask64


class Command(BaseCommand):
    help = "Update user bitmap using celery task"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("bitmap", type=str, nargs="?", default=None)
        parser.add_argument(
            "--immediate",
            action="store_true",
            help="Run the task immediately instead of delaying it",
        )

    def handle(self, username, immediate=False, *args, **options):
        self.stdout.write(f"Get user with username: {username}")
        self.stdout.write(f"Immediate: {immediate}")
        user = User.objects.get(username=username)
        self.stdout.write(f"User: pk={user.id} \033[34m{user.username}\033[0m")
        # currrent user bitmap
        user_current_bitmap = user.bitmap.bitmap
        user_bitmask = BitMask64(user.bitmap.bitmap)

        self.stdout.write(f"user SAVED bitmap():\n  \033[34m{str(user_bitmask)}\033[0m")
        user_expected_bitmap = user.bitmap.get_up_to_date_bitmap()
        user_expected_bitmask = BitMask64(user_expected_bitmap)
        self.stdout.write(
            f"user EXPECTED get_up_to_date_bitmap():\n  \033[34m{str(user_expected_bitmask)}\033[0m"
        )
        difference = int(user_bitmask) ^ int(user_expected_bitmask)
        self.stdout.write(
            f"SAVED ^ EXPECTED difference:\n  \033[34m{bin(difference)}\033[0m"
        )
        if immediate:
            # collection_id, user_id, items_ids_to_add=[], items_ids_to_remove=[]
            instance = update_user_bitmap_task(
                user_id=user.id,
            )

            self.stdout.write(
                f"\nTask returned this updated bitmap: \n  \033[34m{instance.get('bitmap')}\033[0m\n\n"
            )
            self.stdout.write(
                f"Task returned this serialized object: \n  \033[34m{instance}\033[0m\n\n"
            )
            return
        # collection_id, user_id, items_ids_to_add=[], items_ids_to_remove=[]
        message = update_user_bitmap_task.delay(
            user_id=user.id,
        )
        self.stdout.write(f"\n5. Task \033[36m{message}\033[0m launched, check celery.")
