from django.apps import AppConfig


class ImpressoConfig(AppConfig):
    name = "impresso"
    verbose_name = "Impresso"

    def ready(self):
        # we import the signal handler inside the ready() method to avoid import issues
        from django.db.models.signals import post_migrate
        from .signals import create_default_groups

        post_migrate.connect(create_default_groups, sender="impresso")
