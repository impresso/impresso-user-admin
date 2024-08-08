from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from impresso.models import UserBitmap
from impresso.models import DatasetBitmapPosition


class Command(BaseCommand):
    help = "Test a user bitmap against a content bitmap"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("bitmap", type=str, nargs="?", default=None)

    def handle(self, username, *args, **options):
        self.stdout.write(f"Get user with username: {username}")
        user = User.objects.get(username=username)
        self.stdout.write(f"User: pk={user.id} \033[34m{user.username}\033[0m")
        # rpint out user groups
        groups = [group.name for group in user.groups.all()]
        self.stdout.write(f"User groups: \n \033[34m{'\n '.join(groups)}\033[0m")
        # print out its related user bitmap. If no one, just create it.
        user_bitmap = user.bitmap.get_up_to_date_bitmap()
        user_bitmap_length = user_bitmap.bit_length()
        # print user_bitmap binary as sequence of 0 and 1
        self.stdout.write(f"user bitmap: \033[34m{bin(user_bitmap)}\033[0m")
        # get the total number of bits
        self.stdout.write(f"user bitmap length: \033[34m{user_bitmap_length}\033[0m")
    
        self.stdout.write(
            f"User bitmap plan max length: \033[34m{UserBitmap.BITMAP_PLAN_MAX_LENGTH}\033[0m"
        )
        # get user subscriptions
        subscriptions = list(
            user.bitmap.subscriptions.values("name", "bitmap_position")
        )
        # verify that the user subscription positions are correct
        self.stdout.write(
            f"User subscriptions: \n \033[34m{'\n '.join([s.get('name') for s in subscriptions])}\033[0m"
        )
        max_subscription_position = max(
            [s["bitmap_position"] for s in subscriptions]
        )
        self.stdout.write(
            f"Max subscription position: \033[34m{max_subscription_position}\033[0m"
        )
        self.stdout.write(
            f"adjusted max subscription position with groups position: \033[34m{max_subscription_position + UserBitmap.BITMAP_PLAN_MAX_LENGTH}\033[0m"
        )
        
        self.stdout.write("Verify other subscriptions til max user bitmap position (the rest should be 0)")
        # get all possible subscriptions
        all_subscriptions = DatasetBitmapPosition.objects.filter(bitmap_position__lte=max_subscription_position).order_by("bitmap_position")
        
        # print out all possible subscriptions
        for subscription in all_subscriptions:
            position = subscription.bitmap_position + 5
            # Calculate the bit position from the end
            bit_position = max_subscription_position + 5 - position
            # Check if the bit at the specified position is 1
            is_set = (user_bitmap & (1 << bit_position)) != 0
            if is_set:
                self.stdout.write(
                    f"\033[34m {subscription.name} at position: {position} is set: {is_set}\033[0m"
                )
            else:
              self.stdout.write(
                  f" {subscription.name} at position: {position} is set: {is_set}"
              )
        self.stdout.write("\n---\nDone! \033[31m❤️\033[0m \n---\n")

