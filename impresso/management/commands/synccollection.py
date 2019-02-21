import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import store_collection, count_items_in_collection
from django.conf import settings


class Command(BaseCommand):
    help = 'count collected items in a collection and syncronize with SOLR'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', nargs='+', type=str)

    def handle(self, *args, **options):
        collections = Collection.objects.filter(pk__in=options['collection_id'])
        self.stdout.write('n. collection to sync: %s' % collections.count())

        for collection in collections:
            self.stdout.write('start syncing collection "%s"(pk=%s)...' % (collection.name, collection.pk))

            try:
                count_items_in_collection.delay(collection_id=collection.pk)
            except Exception as e:
                self.stderr.write(e)
            try:
                store_collection.delay(collection_id=collection.pk)
            except Exception as e:
                self.stderr.write(e)
