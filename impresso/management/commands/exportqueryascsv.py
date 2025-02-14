from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from impresso.models import UserBitmap, Job, Attachment
from impresso.utils.bitmap import check_bitmap_keys_overlap
from impresso.tasks import export_query_as_csv
from django.conf import settings
from impresso.solr import find_all
from impresso.utils.bitmask import BitMask64, is_access_allowed
from impresso.utils.solr import serialize_solr_doc_content_item_to_plain_dict
from impresso.utils.tasks.export import helper_export_query_as_csv_progress


class Command(BaseCommand):
    help = "Export a SOLR query as a CSV file. Query format is the string for the q parameter in the SOLR query."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=str)
        parser.add_argument("q", type=str)
        parser.add_argument(
            "--no_prompt",
            action="store_true",
            help="Do not prompt for confirmation before running the task",
        )
        parser.add_argument(
            "--immediate",
            action="store_true",
            help="Run the function behind the task immediately instead of delaying it with Celery",
        )
        parser.add_argument(
            "--query_hash",
            type=str,
            help="The hash of the query string, if any, used to identify the query in the database",
        )

    def handle(
        self,
        user_id,
        q,
        no_prompt=False,
        immediate=False,
        query_hash="",
        *args,
        **options,
    ):
        self.stdout.write("\n\n--- Export Solr Query as CSV file ---")
        self.stdout.write("Params \033[34m❤️\033[0m")
        self.stdout.write(f"  user_id: {user_id}")
        self.stdout.write(f"  q: {q}")
        self.stdout.write(f"  --no_prompt: {no_prompt}")
        self.stdout.write(f"  --immediate: {immediate}\n\n")

        user = User.objects.get(pk=user_id)

        self.stdout.write('user id: "%s"' % user.pk)
        self.stdout.write('user uid: "%s"' % user.profile.uid)
        self.stdout.write(f"query q: {q}")
        self.stdout.write(
            f"settings.IMPRESSO_SOLR_FIELDS used in `fl` field: {settings.IMPRESSO_SOLR_FIELDS}"
        )
        # print out IMPRESSO_SOLR_URL
        self.stdout.write(
            f"settings.IMPRESSO_SOLR_URL_SELECT: \033[34m{settings.IMPRESSO_SOLR_URL_SELECT}\033[0m"
        )
        # print out user settings from profile
        self.stdout.write("\nuser profile settings:")
        self.stdout.write(
            f"  max_loops_allowed: \033[34m{user.profile.max_loops_allowed}\033[0m"
        )
        self.stdout.write(
            f"  max_parallel_jobs: \033[34m{user.profile.max_parallel_jobs}\033[0m"
        )
        # bitmap
        try:
            user_bitmap_as_int = user.bitmap.get_bitmap_as_int()

        except User.bitmap.RelatedObjectDoesNotExist:
            user_bitmap_as_int = UserBitmap.USER_PLAN_GUEST
            self.stdout.write(
                self.style.WARNING(
                    f"  no bitmap found for user, using default bitmap: {bin(user_bitmap_as_int)}"
                )
            )

        self.stdout.write(
            f"  user_current_bitmap: \033[34m{bin(user_bitmap_as_int)}\033[0m"
        )
        user_bitmap_as_str = BitMask64(user_bitmap_as_int)
        self.stdout.write(f"  user bitmap as str: \033[34m{user_bitmap_as_str}\033[0m")

        # bitmap print out as base64

        # test query
        results = find_all(q=q, fl=settings.IMPRESSO_SOLR_FIELDS)
        self.stdout.write(
            f"\ntotal documents found: {self.style.SUCCESS(results['response']['numFound'])}\n\n"
        )

        if not results["response"]["numFound"]:
            self.stdout.write("    no results found, aborting.")
            return

        # print out first Solr document as content item properties
        self.stdout.write(f"First document found as example:")

        first_doc = results["response"]["docs"][0]
        first_content_item = serialize_solr_doc_content_item_to_plain_dict(first_doc)
        for k, v in first_content_item.items():
            self.stdout.write(f"  {k}: \033[34m{v}\033[0m")

        # check that user has right to export using the bitmaps
        if "_bm_get_tr_i" in first_doc.keys():
            self.stdout.write(
                "\n\nCheck if user has right to export the first result Transcript using the bitmap"
            )
            # if bitmap is a string of 0 and 1, convert it to int first
            first_content_item_bitmap = first_content_item["_bm_get_tr_i"]
            self.stdout.write(
                f" content bitmap: \033[34m{first_content_item_bitmap}\033[0m"
            )
            overlap = is_access_allowed(
                accessor=user_bitmap_as_str,
                content=BitMask64(first_content_item_bitmap),
            )
            if overlap:
                self.stdout.write(
                    self.style.SUCCESS(" user can get the transcript of this document")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        " user has no right to get the transcript this document"
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "  no field `bm_get_tr` found in the first document, user has no right to export the transcript this document"
                )
            )
        if not no_prompt:
            confirm = input(
                self.style.NOTICE(
                    "\n\nDo you want to proceed with exporting the query as CSV? (type 'y' for yes): "
                )
            )
            if confirm.lower() != "y":
                self.stdout.write(
                    self.style.WARNING(
                        "Export cancelled by user. Use --no_prompt optional arg to avoid the confirmation.\n\n"
                    )
                )
                return
        if not immediate:
            export_query_as_csv.delay(
                query=q,
                user_id=user_id,
                description="from command management",
                query_hash=query_hash,
            )
            self.stdout.write('"test" task launched, check celery.')
            self.stdout.write("\n\n---- end ----\n\n")
            return
        # run the function immediately,
        # save current job then start export_query_as_csv task.
        job = Job.objects.create(
            type=Job.EXPORT_QUERY_AS_CSV,
            creator_id=user_id,
            description="from command management",
        )
        attachment = Attachment.create_from_job(job, extension="csv")
        self.stdout.write(f"job created: {job}")
        self.stdout.write(
            f"attachment created: {self.style.SUCCESS(attachment.upload.path)}"
        )
        page, loops, progress = helper_export_query_as_csv_progress(
            job=job,
            query=q,
            query_hash=query_hash,
            user_bitmap_key=user_bitmap_as_str,
        )
        self.stdout.write(f"page: {page}, loops: {loops}, progress: {progress}")
        self.stdout.write("\n\n---- end ----\n\n")
