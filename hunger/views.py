from django.core.urlresolvers import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.shortcuts import redirect

from hunger.models import InvitationCode
from hunger.forms import InviteSendForm
from hunger.utils import setting, now
from hunger.middleware import invite_from_cookie_and_email


class InviteView(FormView):
    """
    Allow a user to send invites.
    """
    template_name = 'hunger/request_invite.html'
    form_class = InviteSendForm
    success_url = reverse_lazy('hunger-verified')

    def form_valid(self, form):
        valid_code = InvitationCode.objects.get(owner=self.request.user,
                                                num_invites__gt=0)
        form.instance.code = valid_code
        form.instance.invited = now()
        form.save()

        return super(InviteView, self).form_valid(form)

    def form_invalid(self, form):
        return super(InviteView, self).form_valid(form)


class NotBetaView(TemplateView):
    """
    Display a message to the user after the invite request is completed
    successfully.
    """
    template_name = 'hunger/not_in_beta.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            verified_redirect = redirect(setting("HUNGER_VERIFIED_REDIRECT"))
            invitations = request.user.invitation_set.all()
            if any(i.used or i.invited for i in invitations):
                print "IN VIEW - used or invited"
                return verified_redirect
            if invite_from_cookie_and_email(request):
                print "IN BETA VIEW - we can get_from_cookie"
                return verified_redirect

        return super(TemplateView, self).dispatch(request, *args, **kwargs)


class VerifiedView(TemplateView):
    """
    Display a message to the user after the invite request is completed
    successfully.
    """
    template_name = 'hunger/verified.html'


class InvalidView(TemplateView):
    """
    Display a message to the user that the invitation code is
    invalid or has already been used.
    """
    template_name = 'hunger/invalid.html'


def verify_invite(request, code=None):
    response = redirect(setting('HUNGER_VERIFIED_REDIRECT'))
    if code:
        response.set_cookie('hunger_code', code)
    return response
