import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import store_collection
from django.conf import settings


class Command(BaseCommand):
    help = 'count collected items in a collection and syncronize with SOLR'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', nargs='+', type=str)

    def handle(self, *args, **options):
        collections = Collection.objects.filter(pk__in=options['collection_id'])
        for collection in collections:
            self.stdout.write('start syncing collection "%s"(pk=%s)...' % (collection.name, collection.pk))

            items = CollectableItem.objects.filter(
                collection = collection,
                content_type = CollectableItem.ARTICLE
            )
            count = items.count()
            items_ids = items.values_list('item_id', flat=True)

            self.stdout.write('  items count: %s' % count)
            self.stdout.write('  items sample: %s' % ','.join(items_ids[:10]))
            # save collection count
            collection.count_items = count
            collection.save()

            # collection.add_items_to_index(items_ids=items_ids[0:10])

            try:
                store_collection.delay(collection_id=collection.pk)
            except Exception as e:
                self.stderr.write(e)
