import requests, random
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Profile


class Command(BaseCommand):
    help = 'Add a color pattern to user profile'

    def add_arguments(self, parser):
        parser.add_argument('user_id', nargs='+', type=int)
        # Named (optional) arguments
        parser.add_argument(
            '--model',
            dest='model',
            help='Select a specific model instead of picking a random one',
        )

    def handle(self, *args, **options):
        for user_id in options['user_id']:
            try:
                profile = Profile.objects.get(user__pk=user_id)
            except Profile.DoesNotExist:
                raise CommandError('User Profile for user "%s" does not exist' % user_id)

            self.stdout.write('Adding pattern to profile for user "%s" ...' % profile.uid)
            self.stdout.write('colormind.io/list - get models ...')

            res = requests.get('http://colormind.io/list/')
            try:
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise CommandError('Api not reachable')

            self.stdout.write('colormind.io/list - received HTTP status: %s' % (res.status_code,))
            self.stdout.write(res.text)

            models = [m for m in res.json().get('result', [])]
            model  = random.choice(models)

            self.stdout.write('available models: %s' % models)

            if 'model' in options:
                if options['model'] in models:
                    model = options['model']
                    self.stdout.write('selected model: %s' % model)
                else:
                    raise CommandError('Selected model is not available.')
            else:
                self.stdout.write('picked random model: %s' % model)


            self.stdout.write('colormind.io/api - get colors ...')
            res = requests.get('http://colormind.io/api/', data='{"model":"%s"}' % model)

            try:
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise CommandError('Api not reachable')
                break
            # print(e)
            #     break

            self.stdout.write('colormind.io/api - Received HTTP status: %s' % (res.status_code,))
            self.stdout.write(res.text)

            colors = ['#%02x%02x%02x' % tuple(c) for c in res.json().get('result', [])]

            self.stdout.write('colors: %s' % colors)
            gradients = []

            for k, c in enumerate(colors):
                start = round(k / len(colors) * 100)
                stop  = round((k + 1.0) / len(colors) * 100)
                gradients.append('%s %s%%,%s %s%%' % (c, start, c, stop,))

            background_image = 'linear-gradient(60deg,%s)' % ','.join(gradients)
            self.stdout.write('background-image: %s' % background_image)
            self.stdout.write('colors: %s' % colors)

            profile.pattern=','.join(colors)
            profile.save()

            self.stdout.write(self.style.SUCCESS('Successfully added pattern to profile for user "%s"' % profile.uid))
