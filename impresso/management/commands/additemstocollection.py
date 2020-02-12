import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import store_collection, count_items_in_collection
from django.conf import settings


class Command(BaseCommand):
    help = 'add specific articles id to a specific collection. Usage: ENV=prod pipenv run ./manage.py additemstocollection local-dg-AN5AoosL IMP-2005-04-28-a-i0365 LSE-1924-03-07-a-i0026'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', type=str)
        parser.add_argument('items_ids', nargs='+', type=str)

    def handle(self, *args, collection_id, items_ids, **options):
        self.stdout.write('sync: %s' % collection_id)
        collection = Collection.objects.get(pk=collection_id)
        self.stdout.write('start syncing collection "%s"(pk=%s)...' % (collection.name, collection.pk))
        self.stdout.write('items: %s' % items_ids)
        result = collection.add_items_to_index(items_ids=items_ids)
        self.stdout.write('result: %s' % result)
