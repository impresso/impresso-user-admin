import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import add_to_collection_from_query
from django.conf import settings


class Command(BaseCommand):
    help = 'Add content items from a solr query'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', type=str)
        parser.add_argument('q', type=str)

    def handle(self, collection_id, q, *args, **options):
        collection = Collection.objects.get(pk=collection_id)
        self.stdout.write('\n\n--- start ---')
        self.stdout.write('collection to fill: "%s"' % collection.pk)
        self.stdout.write('query: "%s"' % q)

        add_to_collection_from_query.delay(
            collection_id = collection.pk,
            user_id = collection.creator.pk,
            query = q,
            content_type = CollectableItem.ARTICLE
        )
        self.stdout.write('"add_to_collection_from_query" launched, check celery.')
        self.stdout.write('---- end ----\n\n')
