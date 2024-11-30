from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, Group
from ....models import Profile, UserBitmap, DatasetBitmapPosition
from ....utils.tasks.userBitmap import helper_update_user_bitmap
import base64
from django.utils import timezone
from dateutil.parser import isoparse


class TestUserBitmap(TestCase):
    """
    Test the task helper for update_user_bitmap_task
    """

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

    # helper_update_user_bitmap
    def test_helper_update_user_bitmap(self):
        self._helper_update_user_bitmap_guest_to_basic()

    def _helper_update_user_bitmap_guest_to_basic(self):
        """
        Test the helper_update_user_bitmap function.
        """
        serialized = helper_update_user_bitmap(self.user.id)
        decoded_bytes = base64.b64decode(serialized["bitmap"])
        integer_value = int.from_bytes(decoded_bytes, byteorder="big", signed=False)

        self.assertEqual(
            integer_value,
            UserBitmap.USER_PLAN_GUEST,
            "User hasn't accepted the terms of use!",
        )

        # accept the terms of use
        date_accepted_terms = timezone.now().replace(microsecond=0)
        self.userBitmap.date_accepted_terms = date_accepted_terms
        self.userBitmap.save()

        serialized = helper_update_user_bitmap(self.user.id)
        decoded_bytes = base64.b64decode(serialized["bitmap"])
        integer_value = int.from_bytes(decoded_bytes, byteorder="big", signed=False)

        self.assertEqual(
            integer_value,
            UserBitmap.USER_PLAN_AUTH_USER,
            "User has accepted the terms of use, plan is updated",
        )
        self.assertEqual(
            date_accepted_terms.isoformat(timespec="seconds").split("+")[0],
            serialized["date_accepted_terms"].split("Z")[0],
            "Date of terms acceptance is updated",
        )

        # self.assertEqual(
        #     serialized,
        #     {
        #         "date_accepted_terms": None,
        #         "bitmap": None,
        #         "subscriptions": [],
        #         "bitmap": bin(self.userBitmap.get_bitmap_as_int()),
        #         "plan": self.userBitmap.get_user_plan(),
        #     },
        # )
        # accept terms
