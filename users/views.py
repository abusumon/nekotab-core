import logging
from threading import Lock

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.core.mail import send_mail
from django.http.response import Http404
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView

from actionlog.mixins import LogActionMixin
from actionlog.models import ActionLogEntry
from tournaments.mixins import TournamentMixin
from utils.misc import reverse_tournament
from utils.mixins import AdministratorMixin

from .forms import AcceptInvitationForm, InviteUserForm, PublicSignupForm, SuperuserCreationForm
from .tokens import email_verification_token

User = get_user_model()
logger = logging.getLogger(__name__)


class BlankSiteStartView(FormView):
    """This view is presented to the user when there are no tournaments and no
    user accounts. It prompts the user to create a first superuser. It rejects
    all requests, GET or POST, if there exists any user account in the
    system."""

    form_class = SuperuserCreationForm
    template_name = "blank_site_start.html"
    lock = Lock()
    success_url = reverse_lazy('tabbycat-index')

    def get(self, request):
        if User.objects.exists():
            logger.warning("Tried to get the blank-site-start view when a user account already exists.")
            return redirect('tabbycat-index')

        return super().get(request)

    def post(self, request):
        with self.lock:
            if User.objects.exists():
                logger.warning("Tried to post the blank-site-start view when a user account already exists.")
                messages.error(request, _("Whoops! It looks like someone's already created the first user account. Please log in."))
                return redirect('login')

            return super().post(request)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.info(self.request, _("Welcome! You've created an account for %s.") % user.username)

        return super().form_valid(form)


class InviteUserView(LogActionMixin, AdministratorMixin, TournamentMixin, PasswordResetView):
    """This view is used by an administrator to invite an email address to
    either create an account or to give them access to a particular tournament,
    for when permissions will be created."""

    form_class = InviteUserForm
    template_name = "invite_user.html"
    action_log_type = ActionLogEntry.ActionType.USER_INVITE
    page_title = _("Invite User")
    page_emoji = '👤'

    subject_template_name = 'account_invitation_subject.txt'
    email_template_name = 'account_invitation_email.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tournament'] = self.tournament
        return kwargs

    def get_success_url(self):
        return reverse_tournament('options-tournament-index', self.tournament)

    def form_valid(self, form):
        form.save(
            extra_email_context=None,
            use_https=self.request.is_secure(),
            request=self.request,
        )
        messages.success(self.request, _("Successfully invited user to create an account for the tournament."))

        return super().form_valid(form)


class AcceptInvitationView(TournamentMixin, PasswordResetConfirmView):
    form_class = AcceptInvitationForm
    success_url = reverse_lazy('tabbycat-index')
    template_name = 'signup.html'
    page_title = _('Accept Invitation')

    def get_context_data(self, **kwargs):
        if not self.validlink:
            raise Http404
        return super().get_context_data(**kwargs)


class PublicSignupView(FormView):
    """A view for public user registration.

    Creates an inactive account and sends a verification email.  The user
    must click the link in the email to activate the account.
    """

    form_class = PublicSignupForm
    template_name = "public_signup.html"
    success_url = reverse_lazy('tabbycat-index')

    def dispatch(self, request, *args, **kwargs):
        # Redirect if user is already logged in
        if request.user.is_authenticated:
            return redirect('tabbycat-index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()

        # Build verification URL
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        verify_url = self.request.build_absolute_uri(
            reverse('activate-account', kwargs={'uidb64': uid, 'token': token})
        )

        # Send verification email
        subject = _("Verify your NekoTab account")
        body = render_to_string('registration/email_verification.html', {
            'user': user,
            'verify_url': verify_url,
        })
        try:
            send_mail(subject, body, None, [user.email], fail_silently=False)
            messages.success(
                self.request,
                _("Account created! Please check your email to verify your account before logging in."),
            )
        except Exception:
            logger.warning('Failed to send verification email to %s', user.email, exc_info=True)
            messages.warning(
                self.request,
                _("Account created, but we couldn't send a verification email. Please contact an administrator."),
            )

        return super().form_valid(form)


class ActivateAccountView(View):
    """Activate a user account via the token link sent by email."""

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and email_verification_token.check_token(user, token):
            user.is_active = True
            user.save(update_fields=['is_active'])
            login(request, user)
            messages.success(request, _("Your email has been verified. Welcome to NekoTab!"))
            logger.info('User %s verified email and activated account.', user.username)
        else:
            messages.error(request, _(
                "The verification link is invalid or has expired. "
                "Please register again to get a new verification email."
            ))

        return redirect('tabbycat-index')
