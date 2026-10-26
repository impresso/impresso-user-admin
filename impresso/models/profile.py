from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """Store application-specific account data for a Django ``User``.

    The one-to-one profile keeps application fields separate from Django's
    reusable authentication model. Affiliation and institutional URL are
    optional at the database level; plan-specific workflows may require them.

    Attributes:
        user: The related Django user. Deleting the user deletes this profile.
        uid: Unique profile identifier, typically prefixed by its provider.
        provider: Authentication provider (``local`` or ``Github``).
        affiliation: User's institution or other affiliation, if supplied.
        institutional_url: URL supporting the user's stated affiliation.
        displayname: Optional name presented to other users.
        picture: Optional URL of the user's profile image.
        pattern: Optional comma-separated hexadecimal color palette.
        email_accepted: Whether the user accepted mailing-list communications.
        email_verified: Whether the user's email address has been verified.
        max_loops_allowed: Maximum loops allowed when saving queries.
        max_parallel_jobs: Maximum concurrent jobs allowed for the user.

    Constants:
        PROVIDER_LOCAL: Provider value for locally authenticated users.
        PROVIDER_CHOICES: Values accepted by the ``provider`` field.
    """

    PROVIDER_LOCAL = "local"
    PROVIDER_CHOICES = (
        (PROVIDER_LOCAL, "local"),
        ("Github", "Github"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    uid = models.CharField(
        max_length=32,
        unique=True,
    )
    provider = models.CharField(
        max_length=10, choices=PROVIDER_CHOICES, default=PROVIDER_LOCAL
    )

    # affiliation, e; g institution if any
    affiliation = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Affiliation"
    )
    institutional_url = models.URLField(
        blank=True, null=True, verbose_name="Institutional URL"
    )

    # social auth fields
    displayname = models.CharField(max_length=100, null=True, blank=True)
    picture = models.URLField(null=True, blank=True)

    # add pattern ;)
    pattern = models.CharField(max_length=100, null=True, blank=True)

    # is in mailing list.
    email_accepted = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    # maximum for save query
    max_loops_allowed = models.IntegerField(default=100)

    # maximum concurrent running jobs
    max_parallel_jobs = models.IntegerField(default=2)

    class Meta:
        verbose_name_plural = "profiles"
        db_table = "profiles"
