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
        self.stdout.write(self.style.HTTP_INFO(f"\nCollections:"))
        self.stdout.write(f"   (db)count()={collections.count()}")
        self.stdout.write(f"   (db)len(collection_ids)={len(collection_ids)}\n\n")
        # check that wanted IDS point to existing collections
        for idx, collection_id in enumerate(collection_ids):
            self.stdout.write(
                self.style.HTTP_INFO(f"   {idx + 1} of {len(collection_ids)}")
            )

            try:
                collection = Collection.objects.get(pk=collection_id)
            except Collection.DoesNotExist:
                collection = None
                self.stdout.write(
                    self.style.NOTICE(f"  collection {collection_id} does not exist")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   OK {collection_id} status={collection.status}"
                    )
                )

            # creation date
            self.stdout.write(
                f"   (db)id = {collection.id} \n"
                f"   (db)date_created = {collection.date_created} \n"
                f"   (db)status = {collection.status} \n"
                f"   (db)name = {collection.name} \n"
                f"   (db)date_last_modified = {collection.date_last_modified} \n"
                f"   (db)creator = {collection.creator.username} \n"
                f"   (db)count_items = {collection.count_items}\n"
                f"   (db)sq = {collection.serialized_search_query}\n"
            )
            # check related collected items
            collitems = CollectableItem.objects.filter(collection_id=collection_id)
            total_content_items_found_in_db = collitems.count()
            self.stdout.write(
                f"   (db)CollectableItem.count()={total_content_items_found_in_db} \n"
            )

            # 1. check content items TAGGED WITH collection_uid
            ci_url = settings.IMPRESSO_SOLR_URL_SELECT
            ci_query = f"ucoll_ss:{collection_id}"
            ci_request = find_all(
                q=ci_query, url=ci_url, fl="id", skip=0, limit=0, sort="id ASC"
            )
            ci_num_found = ci_request["response"]["numFound"]
            # ci_response_header = ci_request["responseHeader"]
            self.stdout.write(
                f"   (solr)url={ci_url} \n"
                f"   (solr)q={ci_query} \n"
                f"   (solr)numFound: {ci_num_found} \n"
            )

            if total_content_items_found_in_db != ci_num_found:
                self.stdout.write(
                    self.style.ERROR(
                        f"   WARNING: content items in db ({total_content_items_found_in_db}) "
                        f"do not match with Solr index ({ci_num_found}) for collection {collection_id}!"
                    )
                )
                break

            self.stdout.write(
                self.style.SUCCESS(
                    f"   OK content items in db ({total_content_items_found_in_db}) "
                    f"match with Solr index ({ci_num_found}) for collection {collection_id}."
                )
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
                f"   (solr)tr url: {tr_url} \n"
                f"   (solr)tr q={tr_query} \n"
                f"   (solr)tr numFound: {tr_num_found} \n"
            )
            # self.stdout.write(
            #     f"\nSolr tr passages index:\n - url: {tr_url} \n - q={tr_query} "
            #     f" \n - numFound: {tr_num_found}\n"
            # )
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
                f"   (solr)tr ci url: {tr_url} \n"
                f"   (solr)tr ci q={tr_query}&fq={{!collapse field=ci_id_s}} \n"
                f"   (solr)tr ci numFound: {tr_ci_num_found} \n"
            )
