import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import store_collection, count_items_in_collection
from django.conf import settings


class Command(BaseCommand):
    help = 'update count for collected items in a collection'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', nargs='+', type=str)

    def handle(self, *args, **options):
        self.stdout.write('sync: %s' % options['collection_id'])
        collections = Collection.objects.filter(pk__in=options['collection_id'])
        self.stdout.write('n. collection to sync: %s' % collections.count())

        for collection in collections:
            self.stdout.write('start updating collection "{}"(pk={})...'.format(collection.name, collection.pk))
            count_in_solr = collection.update_count_items()
            count_in_db = CollectableItem.objects.filter(collection = collection).count()
            self.stdout.write('done, collection "{}"(pk={}) updated, count_items: {}, in db: {}'.format(
                collection.name,
                collection.pk,
                count_in_solr,
                count_in_db,
            ))
