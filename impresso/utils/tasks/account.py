import logging
from django.core import mail
from django.contrib.auth.models import User
from django_registration.backends.activation.views import RegistrationView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

default_logger = logging.getLogger(__name__)


def getEmailsContents(prefix, context):
    txt_content = render_to_string(
        f'emails/{prefix}.txt', context=context)
    html_content = render_to_string(
        f'emails/{prefix}.html', context=context)
    return txt_content, html_content


def send_emails_after_user_registration(
    user_id, logger=default_logger, test=False
):
    logger.info(f'looking for user={user_id}...')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info(f'user={user_id} NOT FOUND!')
        raise

    logger.info(f'user={user_id} active={user.is_active}')
    view = RegistrationView()
    key = view.get_activation_key(user)
    txt_content, html_content = getEmailsContents(
        prefix='account_created_mailto_user',
        context=({
            'user': user,
            'key': key
        })
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject='Access to the impresso interface',
            body=txt_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email, ],
            cc=[settings.DEFAULT_FROM_EMAIL, ],
            reply_to=[settings.DEFAULT_FROM_EMAIL, ])
        emailMessage.attach_alternative(html_content, 'text/html')
        emailMessage.send(fail_silently=False)

    except Exception:
        raise
    try:
        first_message = mail.outbox[0]
        print(first_message.subject)
        print(first_message.body)
    except Exception:
        logger.info(
            'It looks like the mail settings is not a TEST environment :)')
        pass
    # send email to the user to confirm the subscription
