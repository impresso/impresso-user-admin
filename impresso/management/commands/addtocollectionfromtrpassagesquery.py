import logging
from django.core.management.base import BaseCommand
from impresso.models import Collection
from impresso.tasks import add_to_collection_from_tr_passages_query
from impresso.utils.tasks.textreuse import add_tr_passages_query_results_to_collection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    usage ENV=dev pipenv run python ./manage.py addtocollectionfromtrpassagesquery <collection_id> <solr query>

    Example: add to a specific collection all content items where passages belongs to a cluster_id_s
    e.g. ENV=dev pipenv run python ./manage.py addtocollectionfromtrpassagesquery local-dg-C7aXRWeC "cluster_id_s:tr-nobp-all-v01-c8590083914"
    """

    help = "Add content_items to one collection from a solr query on TR_PASSAGES index, collapsed by content_items"

    def add_arguments(self, parser):
        parser.add_argument("collection_id", type=str)
        parser.add_argument("q", type=str)

        parser.add_argument(
            "--immediate",
            action="store_true",
            help="avoid delay tasks using celery (do not use in production)",
        )
        parser.add_argument(
            "--skip",
            type=int,
            default=0,
            action="store",
            help="skip n content items",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            action="store",
            help="skip n content items",
        )

    def handle(
        self, collection_id, q, immediate=False, skip=0, limit=10, *args, **options
    ):
        self.stdout.write(
            f"Command launched with args: collection_id={collection_id}"
            f" query={q} immediate={immediate} skip={skip} limit={limit}"
        )

        collection = Collection.objects.get(pk=collection_id)
        self.stdout.write(f"Collection found: collection.pk={collection.pk}")
        if immediate:
            loop_skip = skip
            (
                page,
                loops,
                progress,
                result,
            ) = add_tr_passages_query_results_to_collection(
                collection_id=collection.pk,
                query=q,
                skip=loop_skip,
                limit=limit,
                # logger=logger,
            )
            self.stdout.write(
                f"progress={progress} page={page} loops={loops} result={result}"
            )
            while page < loops:
                loop_skip = loop_skip + limit
                (
                    page,
                    loops,
                    progress,
                    result,
                ) = add_tr_passages_query_results_to_collection(
                    collection_id=collection.pk,
                    query=q,
                    skip=loop_skip,
                    limit=limit,
                    # logger=logger,
                )
                self.stdout.write(
                    f"progress={progress} page={page} loops={loops} result={result}"
                )
        else:
            add_to_collection_from_tr_passages_query.delay(
                collection_id=collection.pk,
                user_id=collection.creator.pk,
                query=q,
                skip=skip,
                limit=limit
            )
