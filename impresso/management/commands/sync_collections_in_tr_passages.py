from django.core.management.base import BaseCommand
# from impresso.tasks import store_collection, count_items_in_collection
from django.conf import settings
from ...utils.tasks.collection import sync_collections_in_tr_passages


class Command(BaseCommand):
    """
    usage ENV=dev pipenv run python ./manage.py sync_collections_in_tr_passages
    """
    help = 'Add valid collection ids in TR_PASSAGES.'

    def add_arguments(self, parser):
        parser.add_argument('collection_ids', nargs='+', type=str)

    def handle(self, collection_ids, *args, **options):
        self.stdout.write(f'sync: {collection_ids}')
        # get articles in colection_id
        # look for articles tagged with collection id in ucoll_s
        self.stdout.write(
            f'solr endpoint for articles: {settings.IMPRESSO_SOLR_URL_SELECT}')

        for collection_id in collection_ids:
            sync_collections_in_tr_passages(collection_id=collection_id)
