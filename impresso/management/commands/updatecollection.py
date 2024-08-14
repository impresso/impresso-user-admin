from django.core.management.base import BaseCommand
from impresso.models import Collection
from django.contrib.auth.models import User
from impresso.tasks import update_collection


class Command(BaseCommand):
    help = "Manage articles in a user's collection"

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=str)
        parser.add_argument("collection_id", type=str)
        parser.add_argument(
            "--add", nargs="+", type=str, help="List of article IDs to add"
        )
        parser.add_argument(
            "--remove", nargs="+", type=str, help="List of article IDs to remove"
        )

    def handle(self, user_id, collection_id, *args, **options):
        items_to_add = options["add"]
        items_to_remove = options["remove"]
        # Print items to add
        if items_to_add:
            self.stdout.write("\n1. Check items to add:")
            for item in items_to_add:
                self.stdout.write(f" - \033[32m{item}\033[0m")

        # Print items to remove
        if items_to_remove:
            self.stdout.write("\n2. Check items to remove:")
            for item in items_to_remove:
                self.stdout.write(f" - \033[33m{item}\033[0m")

        if not items_to_add and not items_to_remove:
            self.stderr.write(self.style.ERROR("No items to add or remove"))
            return

        self.stdout.write(f"\n3. Get user having user_id: {user_id}")
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR("User not found"))
            return
        self.stdout.write(f" - user found: \033[34m{user.username}\033[0m")

        self.stdout.write(
            f"\n4. Get collection with collection_id: {collection_id} and user_id: {user_id}"
        )
        try:
            collection = Collection.objects.get(id=collection_id, creator=user)
        except Collection.DoesNotExist:
            self.stderr.write(self.style.ERROR("User or collection not found"))
            return
        self.stdout.write(f" - collection found: \033[34m{collection.name}\033[0m")

        # collection_id, user_id, items_ids_to_add=[], items_ids_to_remove=[]
        message = update_collection.delay(
            collection_id=collection.id,
            user_id=user.id,
            items_ids_to_add=items_to_add,
            items_ids_to_remove=items_to_remove,
        )
        self.stdout.write(
            f"\n5. Task \033[36m{message.id}\033[0m launched, check celery."
        )
