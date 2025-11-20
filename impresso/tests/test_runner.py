from django.test.runner import DiscoverRunner
from django.conf import settings
from django.test import override_settings


class TestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        settings.IN_TEST_SUITE = True
        self.celery_override = override_settings(
            CELERY_TASK_ALWAYS_EAGER=True,
            CELERY_TASK_EAGER_PROPAGATES=True,
            CELERY_TASK_STORE_EAGER_RESULT=False,
        )
        self.celery_override.enable()

        super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)

        # Restore original settings after tests are done
        self.celery_override.disable()
        settings.IN_TEST_SUITE = False
