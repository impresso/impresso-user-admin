import requests
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Profile


class Command(BaseCommand):
    help = 'Add a color pattern to user profile'

    def add_arguments(self, parser):
        parser.add_argument('user_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for user_id in options['user_id']:
            try:
                profile = Profile.objects.get(user__pk=user_id)
            except Profile.DoesNotExist:
                raise CommandError('User Profile for user "%s" does not exist' % user_id)

            self.stdout.write('Adding pattern to profile for user "%s" ...' % profile.uid)

            res = requests.get('http://colormind.io/api/', data='{"model":"makoto_shinkai"}')

            try:
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise CommandError('Api not reachable')
                break
            # print(e)
            #     break

            self.stdout.write('Received HTTP status: %s : %s' % (res.status_code, res.text, ))

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
