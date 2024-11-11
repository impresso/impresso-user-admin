import requests
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Store a few auth related information about a site user and custom info.

    Why? because "Reusable apps shouldn’t implement a custom user model.
    A project may use many apps, and two reusable apps that implemented a
    custom user model couldn’t be used together."
    Attributes:
        user (models.OneToOneField): A one-to-one relationship with the User model.
        uid (models.CharField): A unique identifier for the profile.
        provider (models.CharField): The authentication provider, with choices of 'local' or 'Github'.
        displayname (models.CharField): The display name of the user, optional.
        picture (models.URLField): The URL to the user's profile picture, optional.
        pattern (models.CharField): A custom pattern associated with the user, optional.
        email_accepted (models.BooleanField): Indicates if the user has accepted email notifications.
        max_loops_allowed (models.IntegerField): The maximum number of loops allowed for saving queries.
        max_parallel_jobs (models.IntegerField): The maximum number of concurrent running jobs.
    Constants:
        PROVIDER_LOCAL (str): The local provider constant.
        PROVIDER_CHOICES (tuple): The tuple of provider choices.
    Meta:
        verbose_name_plural (str): The plural name for the model.
        db_table (str): The database table name for the model.
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

    # social auth fields
    displayname = models.CharField(max_length=100, null=True, blank=True)
    picture = models.URLField(null=True, blank=True)

    # add pattern ;)
    pattern = models.CharField(max_length=100, null=True, blank=True)

    # is in mailing list.
    email_accepted = models.BooleanField(default=False)

    # maximum for save query
    max_loops_allowed = models.IntegerField(default=100)

    # maximum concurrent running jobs
    max_parallel_jobs = models.IntegerField(default=2)

    class Meta:
        verbose_name_plural = "profiles"
        db_table = "profiles"
