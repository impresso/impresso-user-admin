import os
from io import StringIO
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = 'create a bunch of json file out of dumpdata in the desired order'
    TABLES = [
        'auth.group',
        'auth.user',
        'impresso.profile',
        'impresso.collection',
        'impresso.collectableItem'
    ]

    def prompt_env(self, default="yes"):
        dotenv_filename = '.{0}.env'.format(os.environ.get('ENV', '')) if 'ENV' in os.environ else '.env'
        self.stdout.write('syncing data using env file: {0}'.format(dotenv_filename))
        question = 'Continue using this env file? Type "y" to continue... '

        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            self.stdout.write(question + prompt)
            choice = input().lower().strip()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                self.stdout.write("Please respond with 'yes' or 'no' "
                                 "(or 'y' or 'n').\n")

    def create_fixture(self, app_name, filename):
        buf = StringIO()
        self.stdout.write('create fixture for app: %s in %s' % (app_name, filename))
        call_command('dumpdata', app_name, stdout=buf)
        buf.seek(0)
        with open(filename, 'w') as f:
            f.write(buf.read())

    def handle(self, *args, **options):
        self.prompt_env()

        for t in Command.TABLES:
            self.stdout.write('dumping table: %s' % t)
            self.create_fixture(t, '{0}.json'.format(t))
