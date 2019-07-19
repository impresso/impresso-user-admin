import os
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from .customdumpdata import Command as DumpCommand

class Command(DumpCommand):
    help = 'load fixtures drom a bunch of json files, in the desired order'

    def load_fixture(self, filename):
        self.stdout.write('loading file: %s' % filename)
        # call_command('loaddata', filename)

    def handle(self, *args, **options):
        self.prompt_env()

        for t in DumpCommand.tables:
            self.stdout.write('syncing table: %s' % t)
            self.load_fixture(filename='{0}.json'.format(t))
