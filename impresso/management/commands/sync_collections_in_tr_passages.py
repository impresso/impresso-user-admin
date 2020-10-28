from django.core.management.base import BaseCommand
# from impresso.tasks import store_collection, count_items_in_collection
from django.conf import settings
from ...utils.tasks.collection import sync_collections_in_tr_passages
from ...tasks import update_collections_in_tr_passages


class Command(BaseCommand):
    """
    usage ENV=dev pipenv run python ./manage.py sync_collections_in_tr_passages
    """
    help = 'Add valid collection ids in TR_PASSAGES.'

    def add_arguments(self, parser):
        parser.add_argument('collection_ids', nargs='+', type=str)
        parser.add_argument(
            '--immediate',
            action='store_true',
            help='avoid delay tasks using celery (not use in production)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='use verbose logging',
        )
        parser.add_argument(
            '--skip',
            type=int,
            action='store',
            help='skip n content items',
        )

    def handle(
        self, collection_ids,
        immediate=False, verbose=False, skip=0, *args, **options
    ):
        self.stdout.write(
            f'sync: {collection_ids} '
            f'immediate:{immediate} verbose:{verbose} skip:{skip}')
        # get articles in colection_id
        # look for articles tagged with collection id in ucoll_s
        self.stdout.write(
            f'solr endpoint for articles: {settings.IMPRESSO_SOLR_URL_SELECT}')
        if not immediate:
            self.stdout.write('delay task: update_collection_in_tr_passages')
            for collection_id in collection_ids:
                update_collections_in_tr_passages.delay(
                    collection_prefix=collection_id)
            return
        for collection_id in collection_ids:
            page = skip/100
            loops = page + 1
            while page < loops:
                page, loops, progress = sync_collections_in_tr_passages(
                    collection_id=collection_id,
                    skip=page*100,
                    limit=100)
                self.stdout.write(
                    f'p:{page}, pages:{loops}, progress:{progress}')
