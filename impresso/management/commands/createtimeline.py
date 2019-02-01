import requests, random
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Newspaper, Issue, Page
from django.conf import settings
from django.db.models import Count, F

class Command(BaseCommand):
    help = 'Add a bunch of timeline data for the newspapero'

    def add_arguments(self, parser):
        parser.add_argument('newspaper_id', nargs='+', type=str)
        # Named (optional) arguments
        # parser.add_argument(
        #     '--model',
        #     dest='model',
        #     help='Select a specific model instead of picking a random one',
        # )
    def stats(self, prefix, pages, issues):
        # issues
        all_issues = issues.values("year").annotate(w=Count("id"))
        # pages
        all_pages  = pages.values(t=F("issue__year")).annotate(w=Count("id"))
        corrupted_pages  = pages.filter(is_corrupted=True).values(t=F("issue__year")).annotate(w=Count("id"))
        # corrupted_layout  = pages.filter(is_converted=True).values(t=F("issue__year")).annotate(w=Count("id"))
        empty_pages  = pages.filter(n_tokens=0).values(t=F("issue__year")).annotate(w=Count("id"))

        self.stdout.write(' - '.join([
            self.style.NOTICE(prefix),
            'issues',
            '%s' % all_issues
        ]))
        print(all_issues)
        print("%s"%all_issues.query)
        self.stdout.write(' - '.join([
            self.style.NOTICE(prefix),
            'pages',
            '%s' % all_issues
        ]))
        print(all_pages)
        print("%s"%all_pages.query)
        print('empty')
        print(empty_pages)
        print("%s"%empty_pages.query)
        print('corrupted')
        print(corrupted_pages)
        print("%s"%corrupted_pages.query)


    def handle(self, *args, **options):
        print(settings.IMPRESSO_SOLR_URL_SELECT)
        print(options['newspaper_id'])

        newspapers = Newspaper.objects.filter(pk__in=options['newspaper_id'])

        # global stats
        self.stats(prefix='all newspapers', pages=Page.objects.all(), issues=Issue.objects.all())

        for i, newspaper in enumerate(newspapers):
            self.stdout.write('1. calculate n. issues for "%s" ...' % newspaper.id)
            issues = Issue.objects.filter(newspaper=newspaper)
            pages  = Page.objects.filter(newspaper=newspaper)

            self.stats(prefix='%s ' % newspaper.id, pages=pages, issues=issues)



        # for newspaper_id in options['newspaper_id']:
        #     try:
        #         profile = Profile.objects.get(user__pk=user_id)
        #     except Profile.DoesNotExist:
        #         raise CommandError('User Profile for user "%s" does not exist' % user_id)
        #
        #     self.stdout.write('Adding pattern to profile for user "%s" ...' % profile.uid)
        #     self.stdout.write('colormind.io/list - get models ...')
        #
        #     res = requests.get('http://colormind.io/list/')
        #     try:
        #         res.raise_for_status()
        #     except requests.exceptions.HTTPError as e:
        #         raise CommandError('Api not reachable')
        #
        #     self.stdout.write('colormind.io/list - received HTTP status: %s' % (res.status_code,))
        #     self.stdout.write(res.text)
        #
        #     models = [m for m in res.json().get('result', [])]
        #     model  = random.choice(models)
        #
        #     self.stdout.write('available models: %s' % models)
        #
        #     if 'model' in options:
        #         if options['model'] in models:
        #             model = options['model']
        #             self.stdout.write('selected model: %s' % model)
        #         else:
        #             raise CommandError('Selected model is not available.')
        #     else:
        #         self.stdout.write('picked random model: %s' % model)
        #
        #
        #     self.stdout.write('colormind.io/api - get colors ...')
        #     res = requests.get('http://colormind.io/api/', data='{"model":"%s"}' % model)
        #
        #     try:
        #         res.raise_for_status()
        #     except requests.exceptions.HTTPError as e:
        #         raise CommandError('Api not reachable')
        #         break
        #     # print(e)
        #     #     break
        #
        #     self.stdout.write('colormind.io/api - Received HTTP status: %s' % (res.status_code,))
        #     self.stdout.write(res.text)
        #
        #     colors = ['#%02x%02x%02x' % tuple(c) for c in res.json().get('result', [])]
        #
        #     self.stdout.write('colors: %s' % colors)
        #     gradients = []
        #
        #     for k, c in enumerate(colors):
        #         start = round(k / len(colors) * 100)
        #         stop  = round((k + 1.0) / len(colors) * 100)
        #         gradients.append('%s %s%%,%s %s%%' % (c, start, c, stop,))
        #
        #     background_image = 'linear-gradient(60deg,%s)' % ','.join(gradients)
        #     self.stdout.write('background-image: %s' % background_image)
        #     self.stdout.write('colors: %s' % colors)
        #
        #     profile.pattern=','.join(colors)
        #     profile.save()
        #
        #     self.stdout.write(self.style.SUCCESS('Successfully added pattern to profile for user "%s"' % profile.uid))
