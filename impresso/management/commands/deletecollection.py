from django.core.management.base import BaseCommand
from impresso.models import Collection
from impresso.tasks import remove_collection


class Command(BaseCommand):
    help = 'count collected items in a collection and syncronize with SOLR'

    def add_arguments(self, parser):
        parser.add_argument('collection_ids', nargs='+', type=str)
        parser.add_argument('user_id', type=str)

    def handle(self, user_id, collection_ids, *args, **options):
        self.stdout.write(f'delete: {collection_ids}')
        collections = Collection.objects.filter(pk__in=collection_ids)
        self.stdout.write(f'n. collection to delete: {collections.count()}')
        for collection_id in collection_ids:
            self.stdout.write(
                f'delay task: remove_collection (pk={collection_id})...'
            )
            remove_collection.delay(
                collection_id=collection_id,
                user_id=user_id
            )
