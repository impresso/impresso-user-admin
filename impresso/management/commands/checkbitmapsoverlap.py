# management/commands/checkbitmapsoverlap.py
from django.core.management.base import BaseCommand, CommandError
from impresso.utils.bitmap import check_bitmap_keys_overlap


# usage:
# ENV=test pipenv run python  manage.py checkbitmapsoverlap 010000000000000000000000000000 00110
class Command(BaseCommand):
    help = "Check if two bitmaps overlap"

    def add_arguments(self, parser):
        parser.add_argument("bitmap1", type=str, help="First bitmap as a string")
        parser.add_argument("bitmap2", type=str, help="Second bitmap as a string")

    def handle(self, *args, **options):
        bitmap1_str = options["bitmap1"]
        bitmap2_str = options["bitmap2"]

        self.stdout.write(f"Bitmap 1:\n \033[34m{bitmap1_str}\033[0m")
        self.stdout.write(f"Bitmap 2:\n \033[34m{bitmap2_str}\033[0m")
        # Check for bitmap overlap
        overlap = check_bitmap_keys_overlap(bitmap1_str, bitmap2_str)

        if overlap:
            self.stdout.write(self.style.SUCCESS("The bitmaps overlap.\n"))
        else:
            self.stdout.write(self.style.WARNING("The bitmaps do not overlap.\n"))
