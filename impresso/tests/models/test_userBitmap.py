from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, Group
from ...models import Profile, UserBitmap, DatasetBitmapPosition
from django.utils import timezone
from ...utils.bitmask import BitMask64, is_access_allowed


class UserBitmapTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.profile = Profile.objects.create(user=self.user, uid="local-testuser")
        self.userBitmap = UserBitmap.objects.create(
            user=self.user,
        )
        self.groupPlanResearcher = Group.objects.create(
            name=settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
        )
        self.groupPlanEducational = Group.objects.create(
            name=settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
        )
        self.test_subscription_domain_A = DatasetBitmapPosition.objects.create(
            name="Domain of TEST A archives",
        )
        self.test_subscription_domain_B = DatasetBitmapPosition.objects.create(
            name="Domain of TEST B archives",
        )
        self.test_subscription_domain_C = DatasetBitmapPosition.objects.create(
            name="Domain of TEST C archives",
        )
        self.test_subscription_domain_D = DatasetBitmapPosition.objects.create(
            name="Domain of TEST D archives",
        )

    def test_user_bitmap_lifecycle(self):
        self._user_bitmap_guest_to_researcher()
        self._user_bitmap_add_remove_subscriptions()
        self._user_bitmap_check_access_only_auth_user()
        self._user_bitmap_check_access_subscriptions()

    def _user_bitmap_guest_to_researcher(self):
        self.assertEqual(
            str(self.userBitmap),
            f"testuser Bitmap {bin(UserBitmap.USER_PLAN_GUEST)}",
            "User has only access to public domain content as the terms have not been accepted yet",
        )
        # the user accepts the terms:
        self.userBitmap.date_accepted_terms = timezone.now()
        self.userBitmap.save()
        # get the latest bitmap
        # updated_bitmap = self.userBitmap.get_up_to_date_bitmap()
        self.assertEqual(
            str(self.userBitmap),
            f"testuser Bitmap {bin(UserBitmap.USER_PLAN_AUTH_USER)}",
            "User has only access to public domain content as the terms have not been accepted yet",
        )
        # just add user to the researcher group
        self.user.groups.add(self.groupPlanResearcher)
        # test update_user_bitmap_on_user_groups_changed signal
        self.userBitmap.refresh_from_db()

        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_RESEARCHER,
            "User has access to Researcher content",
        )
        # if we change the terms of use, the bitmap should be updated
        self.userBitmap.date_accepted_terms = None
        self.userBitmap.save()
        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_GUEST,
            "User has access to public domain content if the terms changed and have not been accepted",
        )

    def _user_bitmap_add_remove_subscriptions(self):
        self.userBitmap.date_accepted_terms = timezone.now()
        self.userBitmap.save()

        self.userBitmap.subscriptions.add(
            self.test_subscription_domain_B,
        )
        # adding a subscription trigger a post_save, let's get it back
        self.userBitmap.refresh_from_db()
        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            0b1001011,
            "User researcher has access to subscription TEST B",
        )

        # remove the subscription to B and add the subscription to A
        self.userBitmap.subscriptions.remove(self.test_subscription_domain_B)
        self.userBitmap.subscriptions.add(self.test_subscription_domain_A)
        self.userBitmap.refresh_from_db()

        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            0b101011,
            "User researcher has access to subscription TEST A",
        )

        self.userBitmap.subscriptions.add(
            self.test_subscription_domain_C,
        )
        self.userBitmap.refresh_from_db()
        self.assertEqual(
            [x for x in self.userBitmap.subscriptions.values_list("name", flat=True)],
            ["Domain of TEST A archives", "Domain of TEST C archives"],
        )
        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            0b10101011,
            f"User researcher has access to subscription TEST A and TEST C, current:{bin(self.userBitmap.get_bitmap_as_int())}",
        )

    def _user_bitmap_check_access_only_auth_user(self):
        user_bitmask = BitMask64(self.userBitmap.bitmap)
        content_bitmask = BitMask64(2)
        self.assertEqual(
            str(content_bitmask),
            "0000000000000000000000000000000000000000000000000000000000000010",
            "Content 10 is accessible to all authenticated users",
        )
        result = is_access_allowed(user_bitmask, content_bitmask)
        self.assertTrue(result, "User has access to content 2")

    def _user_bitmap_check_access_subscriptions(self):
        # use has now two subscriptions, A and C
        self.assertEqual(
            [x for x in self.userBitmap.subscriptions.values_list("name", flat=True)],
            ["Domain of TEST A archives", "Domain of TEST C archives"],
            "User has access to subscription TEST A and TEST C",
        )

        user_bitmask = BitMask64(self.userBitmap.bitmap)
        self.assertEqual(
            str(user_bitmask),
            "0000000000000000000000000000000000000000000000000000000010101011",
            "User researcher has access to subscription TEST A and TEST C",
        )
        content_bitmask = BitMask64(0b100000100)
        self.assertEqual(
            str(content_bitmask),
            "0000000000000000000000000000000000000000000000000000000100000100",
            "Content 0b100000100 is only accessible to students and to a D subscribers",
        )
        self.assertFalse(
            is_access_allowed(user_bitmask, content_bitmask),
            "User does NOT have access to content {content_bitmask}",
        )
        # add the correct subscription
        self.userBitmap.subscriptions.add(self.test_subscription_domain_D)
        self.userBitmap.refresh_from_db()
        self.assertTrue(
            is_access_allowed(BitMask64(self.userBitmap.bitmap), content_bitmask),
            f"User now has finally access to content subscription D! {content_bitmask}",
        )

        content_bitmask = BitMask64(10)
        self.assertEqual(
            str(content_bitmask),
            "0000000000000000000000000000000000000000000000000000000000001010",
        )

        result = is_access_allowed(user_bitmask, content_bitmask)
        self.assertTrue(result, "User has still access to content 1010....")

        # clear all subscription!
        self.userBitmap.subscriptions.clear()
        self.userBitmap.refresh_from_db()
        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_RESEARCHER,
            "User researcher subscriptions cleared. They have no more access to datasets...",
        )
        self.assertFalse(
            is_access_allowed(
                accessor=BitMask64(self.userBitmap.bitmap),
                content=BitMask64(0b100000100),
            ),
            "However, user has no more access to content subscription D!",
        )
