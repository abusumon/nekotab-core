from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView, View
from django.views.generic.edit import CreateView

from users.permissions import Permission

from .forms import InviteMemberForm, WorkspaceTournamentCreateForm
from .models import ClubMemberProfile, OrganizationInvitation, OrganizationMembership
from .workspace_mixins import WorkspaceAccessMixin, WorkspaceAdminMixin


def workspace_page_not_found(request, exception):
    """Custom 404 handler for workspace subdomains.

    Uses the workspace 404 template instead of the main site's 404.html,
    which references URL names that don't exist in the workspace URLconf.
    """
    template = loader.get_template('organizations/workspace/404.html')
    org = getattr(request, 'tenant_organization', None)
    context = {
        'organization': org,
        'request': request,
    }
    return HttpResponseNotFound(template.render(context, request))


class WorkspaceDashboardView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'dashboard'
        ctx['active_tournaments'] = self.organization.tournaments.filter(active=True)
        ctx['member_count'] = self.organization.memberships.count()
        ctx['total_tournament_count'] = self.organization.tournaments.count()
        ctx['archived_tournament_count'] = self.organization.tournaments.filter(active=False).count()
        return ctx


class TournamentListView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/tournament_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'tournaments'
        ctx['tournaments'] = self.organization.tournaments.all().order_by('-created_at')
        return ctx


class TournamentCreateView(WorkspaceAdminMixin, CreateView):
    form_class = WorkspaceTournamentCreateForm
    template_name = 'organizations/workspace/tournament_create.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'tournaments'
        return ctx

    def form_valid(self, form):
        from breakqual.models import BreakCategory
        from breakqual.utils import auto_make_break_rounds
        from tournaments.forms import TournamentStartForm
        from tournaments.utils import auto_make_rounds
        from users.models import UserPermission

        tournament = form.save(commit=False)
        tournament.organization = self.organization
        tournament.owner = self.request.user
        tournament.active = True
        tournament.save()

        # Create initial preliminary rounds
        auto_make_rounds(tournament, form.cleaned_data['num_prelim_rounds'])

        # Create open break category if break size specified
        break_size = form.cleaned_data.get('break_size')
        if break_size:
            open_break = BreakCategory(
                tournament=tournament,
                name=_("Open"),
                slug="open",
                seq=1,
                break_size=break_size,
                is_general=True,
                priority=100,
            )
            open_break.full_clean()
            open_break.save()

        # Generate break rounds (SF, GF, etc.) if a break category exists
        open_break = BreakCategory.objects.filter(tournament=tournament, is_general=True).first()
        if open_break and not tournament.break_rounds().exists():
            auto_make_break_rounds(open_break, tournament, False)

        # Create default permission groups and feedback questions
        TournamentStartForm.add_default_permission_groups(tournament)
        TournamentStartForm.add_default_feedback_questions(tournament)

        # Set current round
        tournament.current_round = tournament.round_set.order_by('seq').first()
        tournament.save()

        # Grant the creator all permissions on this tournament
        UserPermission.objects.bulk_create([
            UserPermission(user=self.request.user, permission=perm, tournament=tournament)
            for perm in Permission
        ], ignore_conflicts=True)

        # Warm the subdomain-exists cache so the redirect lands immediately
        cache.set(f'subdom_tour_exists_{tournament.slug.lower()}', True, 300)

        return redirect('/tournaments/')


class MembersView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/members.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'members'
        ctx['members'] = self.organization.memberships.select_related('user', 'profile').order_by('role')
        ctx['pending_invitations'] = OrganizationInvitation.objects.filter(
            organization=self.organization,
            accepted_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at')
        return ctx


class SettingsView(WorkspaceAdminMixin, TemplateView):
    template_name = 'organizations/workspace/settings.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'settings'
        return ctx


class ArchiveView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/archive.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'archive'
        ctx['archived_tournaments'] = self.organization.tournaments.filter(active=False)
        return ctx


# ---------------------------------------------------------------------------
# Member Invitation System
# ---------------------------------------------------------------------------

class InviteMemberView(WorkspaceAdminMixin, FormView):
    template_name = 'organizations/workspace/invite_member.html'
    form_class = InviteMemberForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'members'
        return ctx

    def form_valid(self, form):
        invitation = OrganizationInvitation(
            organization=self.organization,
            email=form.cleaned_data['email'],
            name=form.cleaned_data['name'],
            role=form.cleaned_data['role'],
            phone=form.cleaned_data.get('phone', ''),
            department=form.cleaned_data.get('department', ''),
            batch=form.cleaned_data.get('batch', ''),
            designation=form.cleaned_data.get('designation', ''),
            invited_by=self.request.user,
        )
        invitation.save()
        self._send_invitation_email(invitation)
        messages.success(
            self.request,
            _("Invitation sent to %(email)s.") % {'email': invitation.email},
        )
        return redirect('/members/')

    def _send_invitation_email(self, invitation):
        accept_url = self.request.build_absolute_uri(
            f"/accept-invitation/{invitation.token}/",
        )
        subject = _("You're invited to join %(org)s on NekoTab") % {
            'org': self.organization.name,
        }
        body = render_to_string('emails/org_invitation.txt', {
            'invitation': invitation,
            'organization': self.organization,
            'accept_url': accept_url,
            'inviter': self.request.user,
        })
        try:
            send_mail(
                subject=str(subject),
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
        except Exception:
            pass  # Log in production; don't crash the invitation flow


class AcceptInvitationView(LoginRequiredMixin, View):
    template_name = 'organizations/workspace/accept_invitation.html'

    def _get_invitation(self, token):
        return get_object_or_404(OrganizationInvitation, token=token)

    def get(self, request, token):
        from django.shortcuts import render
        invitation = self._get_invitation(token)
        ctx = {
            'invitation': invitation,
            'organization': invitation.organization,
            'already_accepted': invitation.is_accepted,
            'expired': invitation.is_expired,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, token):
        invitation = self._get_invitation(token)

        if invitation.is_accepted:
            messages.info(request, _("This invitation has already been accepted."))
            return redirect('/')

        if invitation.is_expired:
            messages.error(request, _("This invitation has expired. Please ask an admin to send a new one."))
            return redirect('/')

        # Check if user is already a member
        existing = OrganizationMembership.objects.filter(
            organization=invitation.organization,
            user=request.user,
        ).first()

        if existing:
            messages.info(request, _("You are already a member of this organization."))
        else:
            membership = OrganizationMembership.objects.create(
                organization=invitation.organization,
                user=request.user,
                role=invitation.role,
            )
            ClubMemberProfile.objects.create(
                membership=membership,
                phone=invitation.phone,
                department=invitation.department,
                batch=invitation.batch,
                designation=invitation.designation,
            )

        # Mark invitation accepted
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = request.user
        invitation.save(update_fields=['accepted_at', 'accepted_by'])

        messages.success(
            request,
            _("Welcome to %(org)s!") % {'org': invitation.organization.name},
        )

        # Redirect to the org workspace if accessible
        org = invitation.organization
        if org.is_workspace_enabled:
            subdomain_base = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
            if subdomain_base:
                return redirect(f"https://{org.slug}.{subdomain_base}/")
        return redirect('/')


class RankingsView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/rankings.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'rankings'

        # Aggregate per membership: avg score, session count, wins, win_rate
        rankings = (
            OrganizationMembership.objects
            .filter(organization=self.organization)
            .annotate(
                sessions_attended=Count(
                    'session_participations',
                    filter=Q(session_participations__attended=True),
                    distinct=True,
                ),
                avg_score=Avg('session_participations__score__score'),
                wins=Count(
                    'session_participations__score',
                    filter=Q(session_participations__score__won=True),
                ),
                debates=Count(
                    'session_participations__score__won',
                    filter=Q(session_participations__score__won__isnull=False),
                ),
            )
            .select_related('user', 'profile')
            .order_by('-avg_score', '-sessions_attended')
        )

        # Attach win_rate as a Python-level computed field
        ranked = []
        for m in rankings:
            m.win_rate = (
                round(m.wins / m.debates * 100) if m.debates else None
            )
            ranked.append(m)

        ctx['ranked_members'] = ranked
        ctx['scored_member_count'] = sum(1 for m in ranked if m.avg_score is not None)
        ctx['has_data'] = any(m.avg_score is not None for m in ranked)
        return ctx


class AnalyticsView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/analytics.html'

    def get_context_data(self, **kwargs):
        from django.db.models.functions import TruncMonth
        from practice.models import PracticeSession, SpeakerScore
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'analytics'
        org = self.organization

        ctx['member_count'] = org.memberships.count()
        ctx['tournament_count'] = org.tournaments.count()
        ctx['active_tournament_count'] = org.tournaments.filter(active=True).count()

        sessions = PracticeSession.objects.filter(organization=org)
        ctx['session_count'] = sessions.count()
        ctx['completed_session_count'] = sessions.filter(status='completed').count()

        # Global avg speaker score
        ctx['global_avg_score'] = SpeakerScore.objects.filter(
            participant__session__organization=org,
        ).aggregate(avg=Avg('score'))['avg']

        # Top 5 by avg score
        ctx['top_members'] = (
            OrganizationMembership.objects
            .filter(organization=org)
            .annotate(
                avg_score=Avg('session_participations__score__score'),
                sessions_attended=Count(
                    'session_participations',
                    filter=Q(session_participations__attended=True),
                    distinct=True,
                ),
            )
            .filter(avg_score__isnull=False)
            .select_related('user')
            .order_by('-avg_score')[:5]
        )

        # Sessions by month (last 6 months)
        from django.utils.timezone import now
        import datetime
        cutoff = now().date() - datetime.timedelta(days=180)
        monthly_sessions = (
            sessions.filter(date__gte=cutoff)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        ctx['recent_sessions'] = [
            {
                'month': row['month'].strftime('%b %Y'),
                'count': row['count'],
            }
            for row in monthly_sessions
        ]

        return ctx
