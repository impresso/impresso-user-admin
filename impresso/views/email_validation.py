from django.contrib.auth.models import User
from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from impresso.models import Profile
from impresso.utils.tasks.account import EMAIL_VALIDATION_SALT


def validate_email(request: HttpRequest) -> HttpResponse:
    """
    Validate a signup email address without activating the user account.

    Expects a signed validation token in the GET parameter ``token``.
    Returns HTTP 200 when the user's profile is marked as verified, or
    HTTP 400 when the token is missing, invalid, expired, or cannot be
    matched to an existing user profile.
    """
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

    if user.email.lower() != str(payload.get("email", "")).lower():
        return HttpResponseBadRequest("Invalid validation link.")

    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])

    return render(request, "email_validation_success.html")
