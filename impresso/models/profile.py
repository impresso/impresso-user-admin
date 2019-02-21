import requests
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    """
    Store a few auth related information about a site user and custom info.

    Why? because "Reusable apps shouldn’t implement a custom user model.
    A project may use many apps, and two reusable apps that implemented a
    custom user model couldn’t be used together."

    """
    PROVIDER_LOCAL = 'local'
    PROVIDER_CHOICES = (
        (PROVIDER_LOCAL, 'local'),
        ('Github', 'Github'),
    )

    user        = models.OneToOneField(User, on_delete=models.CASCADE)
    uid         = models.CharField(max_length=32, unique=True,)
    provider    = models.CharField(max_length=10, choices=PROVIDER_CHOICES, default=PROVIDER_LOCAL)

    # social auth fields
    displayname = models.CharField(max_length=100, null=True, blank=True)
    picture     = models.URLField(null=True, blank=True)

    # add pattern ;)
    pattern     = models.CharField(max_length=100, null=True, blank=True)

    # is in mailing list.
    email_accepted = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'profiles'
        db_table = 'profiles'
