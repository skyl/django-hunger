import os.path
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template.loader import get_template
from django.template import Context

from hunger.utils import setting

try:
    from templated_email import send_templated_mail
    templated_email_available = True
except ImportError:
    templated_email_available = False

logger = logging.getLogger(__name__)


def beta_invite(email, code, request, **kwargs):
    """
    Email for sending out the invitation code to the user.
    Invitation URL is added to the context, so it can be rendered with standard
    django template engine.
    """
    context_dict = kwargs.copy()
    if code:
        invite_url = request.build_absolute_uri(
            reverse("hunger-verify", args=[code])
        )
    else:
        # in invitation_code_sent,
        # if the invitation has a user, we do not need a code.
        invite_url = request.build_absolute_uri('/')

    logger.debug("%s %s" % (code, invite_url))

    context_dict.setdefault("invite_url", invite_url)

    context = Context(context_dict)

    templates_folder = setting('HUNGER_EMAIL_TEMPLATES_DIR')
    templates_folder = os.path.join(templates_folder, '')
    from_email = kwargs.get('from_email',
        getattr(settings, 'DEFAULT_FROM_EMAIL'))
    if templates_folder == 'hunger':
        file_extension = 'email'
    else:
        file_extension = None

    if templated_email_available:
        send_templated_mail(
            template_name='invite_email',
            from_email=from_email,
            recipient_list=[email],
            context=context_dict,
            template_dir=templates_folder,
            file_extension=file_extension,
        )
    else:
        plaintext = get_template(
            os.path.join(templates_folder, 'invite_email.txt'))
        html = get_template(os.path.join(
            templates_folder, 'invite_email.html'))

        subject = get_template(os.path.join(templates_folder,
            'invite_email_subject.txt')).render(context)
        to = email
        text_content = plaintext.render(context)
        html_content = html.render(context)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                                     headers={'From': '%s' % from_email})
        msg.attach_alternative(html_content, "text/html")
        msg.send()
