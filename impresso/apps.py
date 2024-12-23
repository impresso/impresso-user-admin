from django.apps import AppConfig


class ImpressoConfig(AppConfig):
    name = "impresso"
    verbose_name = "Impresso"

    def ready(self):
        # we import the signal handler inside the ready() method to avoid import issues
        from django.db.models.signals import post_migrate, post_save, m2m_changed
        from impresso.models import UserBitmap
        from django.contrib.auth.models import User
        from .signals import (
            create_default_groups,
            post_save_user_change_plan_request,
        )

        post_migrate.connect(create_default_groups, sender="impresso")

        post_save.connect(
            post_save_user_change_plan_request,
            sender="impresso.UserChangePlanRequest",
        )
