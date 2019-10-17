import requests, json
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Collection, CollectableItem
from impresso.tasks import remove_collection
from django.conf import settings


class Command(BaseCommand):
    help = 'count collected items in a collection and syncronize with SOLR'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', nargs='+', type=str)

    def handle(self, *args, **options):
        collections = Collection.objects.filter(pk__in=options['collection_id'])
        self.stdout.write('n. collection to delete: %s' % collections.count())
        for collection in collections:
            self.stdout.write('start deleting collection "%s"(pk=%s)...' % (collection.name, collection.pk))

            try:
                remove_collection.delay(collection_id=collection.pk,user_id=collection.creator.pk)
            except Exception as e:
                self.stderr.write(e)
