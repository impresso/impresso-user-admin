from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, Group
from ...models import Profile, UserBitmap, DatasetBitmapPosition
from django.utils import timezone
from ...utils.bitmap import int_to_bytes, is_access_allowed
from ...utils.bitmask import BitMask64


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

    def test_user_bitmap_lifecycle(self):
        self._user_bitmap_guest_to_researcher()
        self._user_bitmap_add_remove_subscriptions()
        self._user_bitmap_check_access_auth_only()

    def _user_bitmap_guest_to_researcher(self):
        self.assertEqual(
            str(self.userBitmap),
            f"testuser Bitmap {bin(UserBitmap.USER_PLAN_GUEST)}",
            "from left to right, user has only access to public domain as the terms have not been accepted yet",
        )
        # the user accepts the terms:
        self.userBitmap.date_accepted_terms = timezone.now()
        self.userBitmap.save()
        # get the latest bitmap
        updated_bitmap = self.userBitmap.get_up_to_date_bitmap()
        self.userBitmap.bitmap = updated_bitmap.to_bytes(
            (updated_bitmap.bit_length() + 7) // 8, byteorder="big"
        )
        self.assertEqual(
            self.userBitmap.bitmap,
            b"\x18",
            "from left to right, user has access to public domain and to content requiring auth ",
        )
        # just add user to the researcher group
        self.user.groups.add(self.groupPlanResearcher)
        self.userBitmap.refresh_from_db()

        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_RESEARCHER,
            "from left to right, user has access to public domain and to content requiring auth and to content requiring researcher",
        )
        self.assertEqual(
            self.userBitmap.bitmap,
            b"\x1e",
            "from left to right, user has access to public domain, to content requiring auth and to content requiring researcher",
        )

    def _user_bitmap_add_remove_subscriptions(self):
        test_subscription_domain_A = DatasetBitmapPosition.objects.create(
            name="Domain of TEST A archives",
        )
        test_subscription_domain_B = DatasetBitmapPosition.objects.create(
            name="Domain of TEST B archives",
        )
        self.userBitmap.subscriptions.add(
            test_subscription_domain_B,
        )
        # adding a subscription trigger a post_save, let's get it back
        self.userBitmap.refresh_from_db()
        # now the bitmap should be 0b1111001

        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            0b1111001,
            "from left to right, user researcher has access to subscription TEST B",
        )

        # remove the subscription to B and add the subscription to A
        self.userBitmap.subscriptions.remove(test_subscription_domain_B)
        self.userBitmap.subscriptions.add(test_subscription_domain_A)
        self.userBitmap.refresh_from_db()

        self.assertEqual(
            self.userBitmap.get_bitmap_as_int(),
            0b111101,
            "from left to right, user researcher has access to subscription TEST A",
        )

    def _user_bitmap_check_access_auth_only(self):
        print("userBitmap as int:\n", bin(self.userBitmap.get_bitmap_as_int()))
        print("content as int\n", bin(0b10))
        print("userBitmap:\n", str(BitMask64(self.userBitmap.bitmap)))
        content_permissions_mask_auth_only = BitMask64(0b10)  # NO public domain!
        print(
            "content_permissions_mask_auth_only:\n",
            str(content_permissions_mask_auth_only),
        )
