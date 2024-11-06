from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from impresso.models import UserBitmap, Job, Attachment
from impresso.utils.bitmap import check_bitmap_keys_overlap
from impresso.tasks import export_query_as_csv
from django.conf import settings
from impresso.solr import find_all, solr_doc_to_content_item
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

    def handle(self, user_id, q, no_prompt=False, immediate=False, *args, **options):
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
            user_bitmap = user.bitmap.get_up_to_date_bitmap()

        except User.bitmap.RelatedObjectDoesNotExist:
            user_bitmap = UserBitmap.USER_PLAN_GUEST
            self.stdout.write(
                self.style.WARNING(
                    f"  no bitmap found for user, using default bitmap: {bin(user_bitmap)}"
                )
            )

        self.stdout.write(f"  user_current_bitmap: \033[34m{bin(user_bitmap)}\033[0m")

        # bitmap print out as base64

        # test query
        results = find_all(q=q, fl=settings.IMPRESSO_SOLR_FIELDS)
        self.stdout.write(
            f"\ntotal documents found: {self.style.SUCCESS(results["response"]["numFound"])}\n\n"
        )

        if not results["response"]["numFound"]:
            self.stdout.write("    no results found, aborting.")
            return

        # print out first Solr document as content item properties
        self.stdout.write(f"First document found as example:")

        first_doc = results["response"]["docs"][0]
        first_content_item = solr_doc_to_content_item(first_doc)
        for k, v in first_content_item.items():
            self.stdout.write(f"  {k}: \033[34m{v}\033[0m")

        # check that user has right to export using the bitmaps
        if "_bitmap_get_tr" in first_content_item.keys():
            self.stdout.write(
                "\n\nCheck if user has right to export the first result Transcript using the bitmap"
            )
            # if bitmap is a string of 0 and 1, convert it to int first
            first_content_item_bitmap = first_content_item["_bitmap_get_tr"]
            user_bitmap_as_str = bin(user_bitmap)[2:]
            self.stdout.write(f" user bitmap: \033[34m{user_bitmap_as_str}\033[0m")
            self.stdout.write(
                f" content bitmap: \033[34m{first_content_item_bitmap}\033[0m"
            )
            overlap = check_bitmap_keys_overlap(
                user_bitmap_as_str, first_content_item_bitmap
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
                query=q, user_id=user_id, description="from command management"
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
            query_hash="",
            user_bitmap_key=user_bitmap_as_str,
        )
        self.stdout.write(f"page: {page}, loops: {loops}, progress: {progress}")
        self.stdout.write("\n\n---- end ----\n\n")
