from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from impresso.models import UserBitmap
from impresso.models import SpecialMembershipDataset
from ...utils.bitmask import BitMask64


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
        groups_list = "\n ".join(groups)
        self.stdout.write(f"User groups: \n \033[34m{groups_list}\033[0m")
        # print out its related user bitmap. If no one, just create it.

        user_bitmask = BitMask64(user.bitmap.bitmap)

        # print user_bitmap binary as sequence of 0 and 1
        self.stdout.write(f"user BitMask64: \033[34m{str(user_bitmask)}\033[0m")
        # # get the total number of bits
        # self.stdout.write(f"user bitmap length: \033[34m{user_bitmap_length}\033[0m")

        # self.stdout.write(
        #     f"User bitmap plan max length: \033[34m{UserBitmap.BITMAP_PLAN_MAX_LENGTH}\033[0m"
        # )
        # get user subscriptions
        subscriptions = list(
            user.bitmap.subscriptions.values("id", "title", "bitmap_position")
        )

        subscription_names = "\n ".join([s.get("title") for s in subscriptions])
        # verify that the user subscription positions are correct
        self.stdout.write(f"User subscriptions: \n \033[34m{subscription_names}\033[0m")
        max_user_subscription_position = (
            max([s["bitmap_position"] for s in subscriptions]) if subscriptions else -1
        )
        self.stdout.write(
            f"Max user subscription position: \033[34m{max_user_subscription_position}\033[0m"
        )

        self.stdout.write(
            "Verify other subscriptions til max user bitmap position (the rest should be 0)"
        )
        # get all possible subscriptions
        all_subscriptions = SpecialMembershipDataset.objects.all().order_by(
            "bitmap_position"
        )
        max_subscription_position = (
            max([s.bitmap_position for s in all_subscriptions])
            if all_subscriptions
            else -1
        )
        self.stdout.write(
            f"Max subscription position: \033[34m{max_subscription_position}\033[0m"
        )

        # print out all possible subscriptions
        for subscription in all_subscriptions:
            position = subscription.bitmap_position
            # Calculate the bit position from the end
            bit_position = position
            # Check if the bit at the specified position is 1
            is_set = (int(user_bitmask) & (1 << bit_position)) != 0
            if is_set:
                self.stdout.write(
                    f"\033[34m \t{subscription.id}\t{subscription.title} at position: {position} is set: {is_set}\033[0m"
                )
            else:
                self.stdout.write(
                    f" {subscription.title} at position: {position} is set: {is_set}"
                )
        self.stdout.write("\n---\nDone! \033[31m❤️\033[0m \n---\n")
