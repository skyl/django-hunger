import logging
import importlib

from django.dispatch import Signal
from hunger.utils import setting

logger = logging.getLogger(__name__)


def invitation_code_sent(sender, invitation, **kwargs):
    """Send invitation code to user.

    Invitation could be InvitationCode or Invitation.
    """
    logger.info("Sending invitation code %s %s" % (sender, invitation))

    if sender.__name__ == 'Invitation':
        email = invitation.email or invitation.user.email
        if invitation.code:
            code = invitation.code.code
        else:
            code = None

    elif sender.__name__ == 'InvitationCode':
        email = kwargs.pop('email', None)
        code = invitation.code

    if not email:
        logger.warn('invitation_code_sent called without email')
        return

    # we can invite a user directly with no code
    # but, if we have no code and no user,
    # we eon't just open it to the email without a code.
    if code is None and not invitation.user:
        logger.warn('Invite with code+email or user')
        return

    bits = setting('HUNGER_EMAIL_INVITE_FUNCTION').rsplit('.', 1)
    module_name, func_name = bits
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    func(email, code, **kwargs)


invite_sent = Signal(providing_args=['invitation'])
invite_sent.connect(invitation_code_sent)
