from django.test import TransactionTestCase

from impresso.models.profile import Profile
from impresso.models.specialMembershipDataset import SpecialMembershipDataset
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    create_special_membership_request,
)

from django.contrib.auth.models import User


class CreateSpecialMembershipRequestTaskTest(TransactionTestCase):
    """
    THis test case verifies the behavior of the create_special_membership_request
    Celery task, ensuring that it correctly handles the creation of special
    membership requests and appropriately deals with duplicate requests.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser-sm", password="12345")
        self.profile = Profile.objects.create(user=self.user, uid="local-testuser-sm")

        self.test_subscription_domain_A = SpecialMembershipDataset.objects.create(
            title="Domain of TEST A archives",
        )

    def test_celery_task_fail_create_special_membership_request(self) -> None:
        # first cretion should be just fine
        result_first = create_special_membership_request(
            user_id=self.user.id,
            subscription_id=self.test_subscription_domain_A.id,
        )
        self.assertEqual(
            result_first["status"],
            "created",
            "The creation of UserSpecialMembershipRequest should be successful.",
        )
        # Second creation with the same user and subscription should just be skipped
        result_duplicate = create_special_membership_request(
            user_id=self.user.id,
            subscription_id=self.test_subscription_domain_A.id,
        )
        self.assertEqual(
            result_duplicate["status"],
            "skipped_duplicate",
            "The duplicate creation of UserSpecialMembershipRequest should be skipped.",
        )
