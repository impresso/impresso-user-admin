from django.contrib.auth.models import User
from django.conf import settings
from django.core import signing
from django.http import HttpResponse, HttpResponseBadRequest

from impresso.models import Profile
from impresso.utils.tasks.account import EMAIL_VALIDATION_SALT


def validate_email(request):
    """Validate a signup email address without activating the user account."""
    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Missing validation token.")

    try:
        payload = signing.loads(
            token,
            salt=EMAIL_VALIDATION_SALT,
            max_age=60 * 60 * 24 * settings.ACCOUNT_ACTIVATION_DAYS,
        )
    except signing.BadSignature:
        return HttpResponseBadRequest("Invalid or expired validation link.")

    try:
        user = User.objects.get(pk=payload["user_id"])
        profile = Profile.objects.get(user=user)
    except (KeyError, User.DoesNotExist, Profile.DoesNotExist):
        return HttpResponseBadRequest("Invalid validation link.")

    if user.email != payload.get("email"):
        return HttpResponseBadRequest("Invalid validation link.")

    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])

    return HttpResponse(
        "Email address verified. Your account still requires manual activation by the Impresso team."
    )
