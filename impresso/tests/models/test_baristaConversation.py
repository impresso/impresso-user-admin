from django.contrib.auth.models import User
from django.test import TestCase

from ...models import BaristaConversation


class BaristaConversationTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="barista-user", password="12345", email="barista@example.com"
        )

    def _get_user_conversation_by_session(
        self, *, user: User, session_id: str
    ) -> BaristaConversation:
        """
        Minimal session lookup helper for retrieving a conversation.
        """
        return BaristaConversation.objects.get(
            user=user,
            barista_session_id=session_id,
        )

    def test_add_and_retrieve_one_conversation(self) -> None:
        created = BaristaConversation.objects.create(
            user=self.user,
            barista_session_id="redis-session-001",
            label="My first Barista chat",
        )

        retrieved = self._get_user_conversation_by_session(
            user=self.user,
            session_id="redis-session-001",
        )

        self.assertEqual(retrieved.pk, created.pk)
        self.assertEqual(retrieved.user_id, self.user.pk)
        self.assertEqual(retrieved.barista_session_id, "redis-session-001")
        self.assertEqual(retrieved.label, "My first Barista chat")
        self.assertIsNotNone(retrieved.date_created)
        self.assertIsNotNone(retrieved.date_last_modified)
