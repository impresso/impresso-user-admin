import sys
from django.core.management.base import BaseCommand
from impresso.models import Collection
from impresso.tasks import remove_collection


class Command(BaseCommand):
    help = "count collected items in a collection and syncronize with SOLR"

    def add_arguments(self, parser):
        parser.add_argument("collection_ids", nargs="+", type=str)
        parser.add_argument("user_id", type=str, help="user id (int) or 'admin'")

    def handle(self, user_id, collection_ids, *args, **options):
        self.stdout.write(self.style.HTTP_INFO(f"\n\ndeletecollection:"))
        self.stdout.write(
            f" - collection_ids={collection_ids} \n - user_id={user_id}\n\n",
        )
        collections = Collection.objects.filter(pk__in=collection_ids)
        self.stdout.write(f"n. collection to delete: {collections.count()}")

        # if user_id is not a number string:
        if not user_id.isdigit() and not user_id == "admin":
            self.stderr.write(
                f"invalid user_id: {user_id}, should be a digit or 'admin'"
            )
            sys.exit(1)

        for collection_id in collection_ids:
            self.stdout.write(f"delay task: remove_collection (pk={collection_id})...")
            try:
                collection = Collection.objects.get(pk=collection_id)
                collection.status = Collection.DELETED
                collection.save()
            except Collection.DoesNotExist:
                self.stdout.write(
                    f"collection {collection_id} does not exist, but let's try to delete it from solr..."
                )
            remove_collection.delay(
                collection_id=collection_id,
                user_id=collection.creator.pk if user_id == "admin" else user_id,
            )
