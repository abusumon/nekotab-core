import logging
from threading import Lock

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.sites.models import Site
from django.contrib.auth.mixins import LoginRequiredMixin
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
from django.views.generic import FormView, TemplateView

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.views import oauth2_login

from actionlog.mixins import LogActionMixin
from actionlog.models import ActionLogEntry
from tournaments.mixins import TournamentMixin
from utils.misc import reverse_tournament
from utils.mixins import AdministratorMixin

from .forms import AcceptInvitationForm, InviteUserForm, PublicSignupForm, SuperuserCreationForm
from .groups import ensure_role_groups
from .permissions import has_full_access
from .tokens import email_verification_token

User = get_user_model()
logger = logging.getLogger(__name__)


class GoogleOAuthLoginGuardView(View):
    """Safely dispatch Google OAuth login to avoid 500s when not configured."""

    def _has_settings_app(self):
        provider_cfg = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
        app_cfg = provider_cfg.get('APP', {}) if isinstance(provider_cfg, dict) else {}
        return bool(app_cfg.get('client_id') and app_cfg.get('secret'))

    def _has_or_link_db_app_for_site(self):
        site_id = getattr(settings, 'SITE_ID', 1)
        try:
            if SocialApp.objects.filter(provider='google', sites__id=site_id).exists():
                return True

            app = SocialApp.objects.filter(provider='google').order_by('id').first()
            if app is None:
                return False

            try:
                site = Site.objects.get(id=site_id)
            except Site.DoesNotExist:
                logger.warning(
                    "Google SocialApp exists but SITE_ID=%s does not exist; cannot link app.",
                    site_id,
                )
                return False

            app.sites.add(site)
            logger.warning(
                "Linked Google SocialApp id=%s to Site id=%s via login guard fallback.",
                app.id,
                site_id,
            )
            return True
        except Exception:
            logger.warning("Couldn't determine/link Google SocialApp availability", exc_info=True)
            return False

    def get(self, request, *args, **kwargs):
        has_settings_app = self._has_settings_app()
        has_db_app = self._has_or_link_db_app_for_site() if not has_settings_app else False

        if not (has_settings_app or has_db_app):
            messages.error(
                request,
                _("Google sign-in isn't configured yet. Please sign in with username/password."),
            )
            return redirect('login')

        try:
            return oauth2_login(request)
        except Exception:
            logger.warning("Google OAuth login dispatch failed", exc_info=True)
            messages.error(
                request,
                _("Google sign-in is temporarily unavailable. Please try username/password sign-in."),
            )
            return redirect('login')


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
        if user.email:
            EmailAddress.objects.update_or_create(
                user=user,
                email__iexact=user.email,
                defaults={'email': user.email, 'verified': True, 'primary': True},
            )
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

    def test_func(self):
        # Inviting can hand out any role, Tab Director included, so it needs
        # full access: not merely membership of some role on this tournament.
        return has_full_access(self.request.user, self.tournament)

    def get(self, request, *args, **kwargs):
        ensure_role_groups(self.tournament)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from tournaments.models import TournamentStaffMembership

        from .models import Membership
        kwargs = super().get_context_data(**kwargs)
        people = {}

        def person(user):
            return people.setdefault(user.pk, {'user': user, 'roles': [], 'staff_roles': []})
        for m in (Membership.objects.filter(group__tournament=self.tournament)
                  .select_related('user', 'group').order_by('user__username')):
            person(m.user)['roles'].append(m)
        for sm in (TournamentStaffMembership.objects.filter(tournament=self.tournament)
                   .select_related('user')):
            person(sm.user)['staff_roles'].append(sm)
        kwargs['owner'] = self.tournament.owner
        kwargs['people'] = [p for uid, p in people.items() if uid != self.tournament.owner_id]
        return kwargs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tournament'] = self.tournament
        return kwargs

    def get_success_url(self):
        # Back to the same page, so the new person shows in "People with access".
        return reverse_tournament('invite-user', self.tournament)

    def form_valid(self, form):
        form.save(
            extra_email_context=None,
            use_https=self.request.is_secure(),
            request=self.request,
        )
        existing = getattr(form, '_invited_existing_user', None)
        if existing:
            messages.success(
                self.request,
                _("%(user)s already has an account — they have been granted access and can log in directly.")
                % {'user': existing.email},
            )
        else:
            messages.success(self.request, _("Successfully invited user to create an account for the tournament."))

        return super().form_valid(form)


class RemoveAccessView(LogActionMixin, AdministratorMixin, TournamentMixin, View):
    """Remove one role (group membership or staff role) from someone. The
    owner's access is not a role and cannot be removed here."""

    action_log_type = ActionLogEntry.ActionType.USER_INVITE

    def test_func(self):
        return has_full_access(self.request.user, self.tournament)

    def post(self, request, *args, **kwargs):
        from tournaments.models import TournamentStaffMembership

        from .models import Membership
        kind, pk = request.POST.get('kind'), request.POST.get('pk')
        model = {'role': Membership, 'staff': TournamentStaffMembership}.get(kind)
        if model is None or not str(pk).isdigit():
            raise Http404
        lookup = {'group__tournament': self.tournament} if model is Membership else {'tournament': self.tournament}
        obj = model.objects.filter(pk=pk, **lookup).select_related('user').first()
        if obj is None:
            raise Http404
        name = obj.user.get_full_name() or obj.user.get_username()
        obj.delete()
        self.log_action()
        messages.success(request, _("Removed that role from %(name)s.") % {'name': name})
        return redirect(reverse_tournament('invite-user', self.tournament))


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

            # Register the verified email with allauth so that future Google
            # sign-ins (email authentication) don't wipe the password.
            EmailAddress.objects.update_or_create(
                user=user,
                email__iexact=user.email,
                defaults={'email': user.email, 'verified': True, 'primary': True},
            )

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, _("Your email has been verified. Welcome to NekoTab!"))
            logger.info('User %s verified email and activated account.', user.username)
        else:
            messages.error(request, _(
                "The verification link is invalid or has expired. "
                "Please register again to get a new verification email."
            ))
            
        # /me, deliberately — unchanged from before the premium branch.
        #
        # This is not the post-login landing that Phase 5 moved to '/'. Somebody
        # arriving here has just clicked a link in their email to finish signing
        # up, and the useful next screen is their own dashboard, not the
        # marketing home page. The two are different moments and want different
        # destinations.
        return redirect('user-dashboard')


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/user_dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        from tournaments.models import Tournament, TournamentMetadata
        from organizations.models import OrganizationMembership, get_user_organizations
        from draw.models import Debate

        my_tournaments = Tournament.objects.filter(owner=user).select_related('metadata').order_by('-created_at')

        # Group by lifecycle status (TournamentMetadata.status when present, else the
        # coarser `active` flag) so the dashboard reads as a history, not just two piles.
        upcoming, in_progress, past = [], [], []
        Status = TournamentMetadata.Status
        for t in my_tournaments:
            metadata = getattr(t, 'metadata', None)
            status = metadata.status if metadata else None
            if status == Status.IN_PROGRESS:
                in_progress.append(t)
            elif status in (Status.COMPLETED, Status.ARCHIVED):
                past.append(t)
            elif status in (Status.DRAFT, Status.REGISTRATION_OPEN, Status.REGISTRATION_CLOSED):
                upcoming.append(t)
            elif t.active:
                upcoming.append(t)
            else:
                past.append(t)

        ctx['upcoming_tournaments'] = upcoming
        ctx['in_progress_tournaments'] = in_progress
        ctx['past_tournaments'] = past
        ctx['total_tournament_count'] = my_tournaments.count()
        ctx['total_debate_count'] = Debate.objects.filter(
            round__tournament__owner=user
        ).count()

        from django.db.models import Q as _Q

        from support.models import SupportTicket
        if user.is_staff or user.is_superuser:
            ctx['open_ticket_count'] = SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count()
        else:
            # Own tickets, plus anything routed to a tournament this user directs.
            ctx['open_ticket_count'] = SupportTicket.objects.filter(
                _Q(user=user) | _Q(tournament__owner=user), status=SupportTicket.Status.OPEN,
            ).distinct().count()

        ctx['user_organizations'] = get_user_organizations(user)

        base_domain = (getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '') or '').strip()
        ctx['primary_workspace_url'] = None
        if base_domain:
            slug = (
                OrganizationMembership.objects.filter(
                    user=user,
                    organization__is_workspace_enabled=True,
                )
                .values_list('organization__slug', flat=True)
                .first()
            )
            if slug:
                ctx['primary_workspace_url'] = f"https://{slug}.{base_domain}/"

        return ctx

        return redirect('tabbycat-index')
