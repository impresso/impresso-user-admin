from django.core.management.base import BaseCommand
from django.conf import settings
from impresso.models import Collection, CollectableItem
from ...solr import find_all


class Command(BaseCommand):
    help = 'Check status of collection(s) in SOLR and db'

    def add_arguments(self, parser):
        parser.add_argument('collection_ids', nargs='+', type=str)

    def handle(self, collection_ids, *args, **options):
        self.stdout.write(f'(args) collection_ids={collection_ids}')
        collections = Collection.objects.filter(pk__in=collection_ids)
        self.stdout.write(f'(args) len(collection_ids)={len(collection_ids)}')
        self.stdout.write(f'(db Collection) count()={collections.count()}')
        for collection_id in collection_ids:
            # 1. check content items
            ci_url = settings.IMPRESSO_SOLR_URL_SELECT
            ci_query = f'ucoll_ss:{collection_id}'
            ci_request = find_all(
                q=ci_query,
                url=ci_url,
                fl='id',
                skip=0,
                limit=0,
                sort='id ASC')
            ci_num_found = ci_request['response']['numFound']
            ci_response_header = ci_request['responseHeader']
            self.stdout.write(
                f'(solr ci) q={ci_query} in {ci_url}'
                f' numFound={ci_num_found}'
                f' responseHeader={ci_response_header}'
            )
            # 1. check in TR passages
            tr_url = settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT
            tr_query = f'ucoll_ss:{collection_id}'
            tr_request = find_all(
                q=tr_query,
                url=tr_url,
                fl='id',
                skip=0,
                limit=0,
                sort='id ASC')
            tr_num_found = tr_request['response']['numFound']
            tr_response_header = tr_request['responseHeader']
            self.stdout.write(
                f'(solr tr) q={tr_query} in {tr_url}'
                f' numFound={tr_num_found}'
                f' responseHeader={tr_response_header}'
            )
            # 3. check collectable_items
            collitems = CollectableItem.objects.filter(
                collection_id=collection_id)
            self.stdout.write(
                f'(db CollectableItem) count()={collitems.count()}'
            )
