import logging

from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

from hunger.models import InvitationCode, Invitation
from hunger.utils import setting, now


logger = logging.getLogger(__name__)


def invite_from_cookie_and_email(request):
    #print 90
    cookie_code = request.COOKIES.get('hunger_code')
    #print "code", cookie_code
    if not cookie_code:
        #print "missed, no cookie, nada,  returning redirect"
        return False

    # No invitation, all we have is this cookie code
    try:
        code = InvitationCode.objects.get(
            code=cookie_code, num_invites__gt=0)
    except InvitationCode.DoesNotExist:
        #print "invalid cookie code"
        request._hunger_delete_cookie = True
        return False

    # try to get the email for the code
    try:
        invite = Invitation.objects.get(
            code=code,
            email=request.user.email
        )
    except Invitation.DoesNotExist:
        request._hunger_delete_cookie = True
        #print "we still need a valid email"
        return False

    return invite


class BetaMiddleware(object):
    """
    Add this to your ``MIDDLEWARE_CLASSES`` make all views except for
    those in the account application require that a user be logged in.
    This can be a quick and easy way to restrict views on your site,
    particularly if you remove the ability to create accounts.

    **Settings:**

    ``HUNGER_ENABLE_BETA``
        Whether or not the beta middleware should be used. If set to
        `False` the BetaMiddleware middleware will be ignored and the
        request will be returned. This is useful if you want to
        disable privatebeta on a development machine. Default is
        `True`.

    ``HUNGER_ALWAYS_ALLOW_VIEWS``
        A list of full view names that should always pass through.

    ``HUNGER_ALWAYS_ALLOW_MODULES``
        A list of modules that should always pass through.  All
        views in ``django.contrib.auth.views``, ``django.views.static``
        and ``hunger.views`` will pass through.

    ``HUNGER_REDIRECT``
        The redirect when not in beta.
    """

    def __init__(self):
        self.enable_beta = setting('HUNGER_ENABLE')
        self.always_allow_views = setting('HUNGER_ALWAYS_ALLOW_VIEWS')
        self.always_allow_modules = setting('HUNGER_ALWAYS_ALLOW_MODULES')
        self.redirect = setting('HUNGER_REDIRECT')
        self.allow_flatpages = setting('HUNGER_ALLOW_FLATPAGES')

    def process_view(self, request, view_func, view_args, view_kwargs):
        #print 0
        if not self.enable_beta:
            return

        #print 1
        if (request.path in self.allow_flatpages or
            (getattr(settings, 'APPEND_SLASH', True) and
             '%s/' % request.path in self.allow_flatpages)):
            from django.contrib.flatpages.views import flatpage
            #print "returning flatpage!"
            return flatpage(request, request.path_info)

        #print 2
        whitelisted_modules = ['django.contrib.auth.views',
                               'django.contrib.admin.sites',
                               'django.views.static',
                               'django.contrib.staticfiles.views',
                               'hunger.views']

        short_name = view_func.__class__.__name__
        if short_name == 'function':
            short_name = view_func.__name__
        view_name = self._get_view_name(request)

        full_view_name = '%s.%s' % (view_func.__module__, short_name)

        if self.always_allow_modules:
            whitelisted_modules += self.always_allow_modules

        if '%s' % view_func.__module__ in whitelisted_modules:
            #print "whitelisted"
            return

        #print 3
        if (full_view_name in self.always_allow_views or
                view_name in self.always_allow_views):
            return

        #print 4
        if not request.user.is_authenticated():
            return redirect(self.redirect)

        #print 5
        if request.user.is_staff:
            return
        #print 6

        # Prevent queries by caching in_beta status in session
        if request.session.get('hunger_in_beta'):
            return

        #print 7

        invitations = request.user.invitation_set.select_related('code')
        #print "USER", request.user, request.user.email
        #print "INVITATIONS", invitations

        if not invitations and not request.COOKIES.get('hunger_code'):
            #print "no invitations, no code for logged in user,"
            #print "make one and redirect"
            invitation = Invitation(
                user=request.user,
                email=request.user.email
            )
            invitation.save()
            return redirect(self.redirect)

        #print 8

        if any([i.used for i in invitations]):
            #print "some are used, therefore we are in Beta"
            request.session['hunger_in_beta'] = True
            return

        #print 9

        # User has been invited - use the invitation and place in beta.
        activates = [i for i in invitations if i.invited and not i.used]
        for invitation in activates:
            #print "let's activate"
            invitation.used = now()
            invitation.save()
            request.session['hunger_in_beta'] = True
            return

        #print 10
        # get from cookie, assume is authenticated and has email.
        invite = invite_from_cookie_and_email(request)
        if invite:
            invite.accept_invite(request.user)
            return
        else:
            return redirect(self.redirect)

    def process_response(self, request, response):
        if getattr(request, '_hunger_delete_cookie', False):
            response.delete_cookie('hunger_code')
        return response

    @staticmethod
    def _get_view_name(request):
        """Return the urlpattern name."""
        if hasattr(request, 'resolver_match'):
            # Django >= 1.5
            return request.resolver_match.view_name

        match = resolve(request.path)
        return match.url_name
