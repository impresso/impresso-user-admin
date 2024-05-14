import requests, json
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Job, Attachment

from impresso.tasks import export_query_as_csv
from django.conf import settings
from impresso.solr import find_all, solr_doc_to_article


class Command(BaseCommand):
    help = "Create a test job with fake progress for a given user"

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=str)
        parser.add_argument("q", type=str)

    def handle(self, user_id, q, *args, **options):
        user = User.objects.get(pk=user_id)

        self.stdout.write("\n\n--- start ---")
        self.stdout.write('user id: "%s"' % user.pk)
        self.stdout.write('user uid: "%s"' % user.profile.uid)
        self.stdout.write(f"query q: {q}")
        self.stdout.write(
            f"query fl settings.IMPRESSO_SOLR_FIELDS: {settings.IMPRESSO_SOLR_FIELDS}"
        )

        # test query
        results = find_all(q=q, fl=settings.IMPRESSO_SOLR_FIELDS)
        self.stdout.write("found docs: (%s)" % results["response"]["numFound"])
        if results["response"]["numFound"] > 0:
            self.stdout.write(
                "row example BEFORE content filtering: (%s)"
                % solr_doc_to_article(results["response"]["docs"][0])
            )
            export_query_as_csv.delay(
                query=q, user_id=user_id, description="from command management"
            )
            self.stdout.write('"test" task launched, check celery.')
        self.stdout.write("---- end ----\n\n")
