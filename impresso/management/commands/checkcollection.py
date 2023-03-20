from django.core.management.base import BaseCommand
from django.conf import settings
from impresso.models import Collection, CollectableItem
from ...solr import find_all


class Command(BaseCommand):
    help = "Check status of collection(s) in SOLR and db"

    def add_arguments(self, parser):
        parser.add_argument("collection_ids", nargs="+", type=str)

    def handle(self, collection_ids, *args, **options):
        self.stdout.write(self.style.HTTP_INFO(f"\n\nCheck collection"))
        self.stdout.write(
            f" - collection_ids={collection_ids}",
        )
        collections = Collection.objects.filter(pk__in=collection_ids)
        self.stdout.write(f"\nCollection in DB collections table:")
        self.stdout.write(f" - count()={collections.count()}")
        self.stdout.write(f" - len(collection_ids)={len(collection_ids)}")

        for collection_id in collection_ids:
            try:
                collection = Collection.objects.get(pk=collection_id)
            except Collection.DoesNotExist:
                collection = None
                self.stdout.write(
                    self.style.NOTICE(f" - collection {collection_id} does not exist")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f" - {collection_id} status={collection.status}")
                )
                self.stdout.write(f"(db) saved items: {collection.count_items}")

            # 1. check content items
            ci_url = settings.IMPRESSO_SOLR_URL_SELECT
            ci_query = f"ucoll_ss:{collection_id}"
            ci_request = find_all(
                q=ci_query, url=ci_url, fl="id", skip=0, limit=0, sort="id ASC"
            )
            ci_num_found = ci_request["response"]["numFound"]
            # ci_response_header = ci_request["responseHeader"]
            self.stdout.write(
                f"\nSolr content item index:\n - url: {ci_url} \n - q={ci_query} "
                f"\n - numFound: {ci_num_found}"
            )
            # self.stdout.write(f" - responseHeader={ci_response_header}")
            # 2. check in TR passages
            tr_url = settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT
            tr_query = f"ucoll_ss:{collection_id}"
            tr_request = find_all(
                q=tr_query, url=tr_url, fl="id", skip=0, limit=0, sort="id ASC"
            )
            tr_num_found = tr_request["response"]["numFound"]
            # tr_response_header = tr_request["responseHeader"]
            self.stdout.write(
                f"\nSolr tr passages index:\n - url: {tr_url} \n - q={tr_query} "
                f" \n - numFound: {tr_num_found}\n"
            )
            # 3. check content items in tr passages and see if there are missing stuff.
            tr_request = find_all(
                q=tr_query,
                url=tr_url,
                fl="id",
                skip=0,
                limit=0,
                sort="id ASC",
                fq="{!collapse field=ci_id_s}",
            )
            tr_ci_num_found = tr_request["response"]["numFound"]
            # tr_response_header = tr_request["responseHeader"]
            self.stdout.write(
                f"\nSolr tr passages index, collapsed by ci:\n - url: {tr_url} \n - q={tr_query} \n - fq=!collapse field=ci_id_s"
                f" \n - numFound: {tr_ci_num_found} \n"
            )

            # self.stdout.write(f" - responseHeader={tr_response_header}")
            # 3. check collectable_items
            collitems = CollectableItem.objects.filter(collection_id=collection_id)
            collitems_num_found = collitems.count()
            self.stdout.write(
                f"\nCollection in DB collections table:"
                f"\n - numFound: {collitems_num_found}"
            )
            if tr_ci_num_found != ci_num_found:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: (solr tr) q={tr_query} in {tr_url}"
                        f" \n - numFound: {tr_ci_num_found} (collapse field=ci_id_s)"
                        f" != {ci_num_found} (ci)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"(solr tr) q={tr_query} in {tr_url}"
                        f" \n - numFound: {tr_ci_num_found} (collapse field=ci_id_s)"
                        f" == {ci_num_found} (ci)"
                    )
                )

            if collitems_num_found != ci_num_found:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: (db CollectableItem) count()={collitems_num_found}"
                        f" != {ci_num_found} (ci)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"(db CollectableItem) count()={collitems_num_found}"
                        f" == {ci_num_found} (ci)"
                    )
                )

            if collection and collection.count_items != ci_num_found:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: (db Collection) {collection_id} count_items={collection.count_items}"
                        f" != {ci_num_found} (ci)"
                    )
                )
            elif collection:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"(db Collection) {collection_id} count_items={collection.count_items}"
                        f" == {ci_num_found} (ci)"
                    )
                )
            elif ci_num_found + tr_ci_num_found + tr_num_found > 0:
                # make sure all count are set to 0
                self.stderr.write(
                    self.style.ERROR(
                        f"ERROR: (db Collection) {collection_id} does not exist anymore, but there are still items in SOLR"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nCollection {collection_id} has been correctly deleted, it does not exist anymore anywhere.\n"
                    )
                )
