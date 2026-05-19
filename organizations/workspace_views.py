import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView, View
from django.views.generic.edit import CreateView

from users.permissions import Permission

from tournaments.models import (
    Tournament,
    TournamentAuditLog,
    TournamentMetadata,
    TournamentStaffInvitation,
    TournamentStaffMembership,
)

from .forms import InviteMemberForm, TournamentStaffInviteForm, WorkspaceTournamentCreateForm
from .models import ClubMemberProfile, OrganizationInvitation, OrganizationMembership, OrgForm, OrgFormResponse
from .workspace_mixins import WorkspaceAccessMixin, WorkspaceAdminMixin


def _permissions_for_staff_role(role):
    all_permissions = set(Permission.values)

    if role == TournamentStaffMembership.Role.TAB_DIRECTOR:
        return all_permissions

    if role == TournamentStaffMembership.Role.ASSISTANT_TAB:
        critical_permissions = {
            Permission.EDIT_SETTINGS,
            Permission.DELETE_ROUND,
            Permission.RELEASE_DRAW,
            Permission.RELEASE_MOTION,
            Permission.UNRELEASE_DRAW,
            Permission.UNRELEASE_MOTION,
        }
        return all_permissions - critical_permissions

    if role == TournamentStaffMembership.Role.EQUITY:
        return {
            Permission.VIEW_FEEDBACK,
            Permission.VIEW_FEEDBACK_OVERVIEW,
            Permission.ADD_FEEDBACK,
            Permission.EDIT_FEEDBACK_CONFIRM,
            Permission.VIEW_ADJ_BREAK,
            Permission.EDIT_ADJ_BREAK,
            Permission.VIEW_RESULTS,
            Permission.VIEW_BREAK,
            Permission.VIEW_BREAK_OVERVIEW,
        }

    if role == TournamentStaffMembership.Role.CONVENOR:
        return {
            Permission.VIEW_TEAMS,
            Permission.ADD_TEAMS,
            Permission.VIEW_ADJUDICATORS,
            Permission.ADD_ADJUDICATORS,
            Permission.VIEW_ROOMS,
            Permission.ADD_ROOMS,
            Permission.VIEW_PARTICIPANTS,
            Permission.VIEW_REGISTRATION,
            Permission.SEND_EMAILS,
            Permission.VIEW_CHECKIN,
            Permission.EDIT_PARTICIPANT_CHECKIN,
        }

    return {
        Permission.VIEW_TEAMS,
        Permission.VIEW_ADJUDICATORS,
        Permission.VIEW_ROOMS,
        Permission.VIEW_DEBATE,
        Permission.VIEW_RESULTS,
    }


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

        query = (self.request.GET.get('q') or '').strip()
        status = (self.request.GET.get('status') or '').strip()

        tournaments = (
            self.organization.tournaments
            .select_related('metadata')
            .annotate(participant_count=Count('team', distinct=True))
            .order_by('-created_at')
        )

        if query:
            tournaments = tournaments.filter(
                Q(name__icontains=query)
                | Q(short_name__icontains=query)
                | Q(slug__icontains=query)
            )

        if status:
            tournaments = tournaments.filter(metadata__status=status)

        ctx['tournaments'] = tournaments
        ctx['query'] = query
        ctx['status'] = status
        ctx['status_choices'] = TournamentMetadata.Status.choices
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

        visibility = form.cleaned_data.get('visibility', TournamentMetadata.Visibility.ORGANIZATION)
        should_list_publicly = visibility == TournamentMetadata.Visibility.PUBLIC
        if tournament.is_listed != should_list_publicly:
            tournament.is_listed = should_list_publicly
            tournament.save(update_fields=['is_listed'])

        metadata = TournamentMetadata.objects.create(
            tournament=tournament,
            event_start_date=form.cleaned_data.get('event_start_date'),
            event_end_date=form.cleaned_data.get('event_end_date'),
            registration_open=form.cleaned_data.get('registration_open'),
            registration_close=form.cleaned_data.get('registration_close'),
            event_format=form.cleaned_data.get('event_format', ''),
            venue=form.cleaned_data.get('venue', ''),
            visibility=visibility,
            registration_type=form.cleaned_data.get('registration_type', TournamentMetadata.RegistrationType.OPEN),
            status=form.cleaned_data.get('lifecycle_status', TournamentMetadata.Status.DRAFT),
        )

        TournamentAuditLog.objects.create(
            tournament=tournament,
            actor=self.request.user,
            action='tournament.created',
            entity_type='tournament',
            entity_id=str(tournament.pk),
            new_value={
                'name': tournament.name,
                'slug': tournament.slug,
                'metadata_id': metadata.pk,
            },
        )

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


class TournamentStaffView(WorkspaceAdminMixin, TemplateView):
    template_name = 'organizations/workspace/tournament_staff.html'

    def dispatch(self, request, *args, **kwargs):
        self.tournament = get_object_or_404(
            Tournament,
            slug=kwargs['tournament_slug'],
            organization=self.organization,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'tournaments'
        ctx['tournament'] = self.tournament
        ctx['staff_memberships'] = (
            self.tournament.staff_memberships
            .select_related('user', 'invited_by')
            .order_by('role', 'user__username')
        )
        ctx['pending_staff_invitations'] = (
            self.tournament.staff_invitations
            .filter(accepted_at__isnull=True, expires_at__gt=timezone.now())
            .order_by('-created_at')
        )
        ctx['invite_form'] = TournamentStaffInviteForm(tournament=self.tournament)
        return ctx


class TournamentStaffInviteView(WorkspaceAdminMixin, View):

    def post(self, request, tournament_slug):
        tournament = get_object_or_404(
            Tournament,
            slug=tournament_slug,
            organization=self.organization,
        )
        form = TournamentStaffInviteForm(request.POST, tournament=tournament)
        if not form.is_valid():
            messages.error(request, _("Couldn't send invitation. Please fix the form and try again."))
            return redirect(f'/tournaments/{tournament.slug}/staff/')

        invitation = TournamentStaffInvitation.objects.create(
            tournament=tournament,
            email=form.cleaned_data['email'],
            role=form.cleaned_data['role'],
            invited_by=request.user,
        )

        self._send_invitation_email(invitation)

        TournamentAuditLog.objects.create(
            tournament=tournament,
            actor=request.user,
            action='tournament.staff.invited',
            entity_type='tournament_staff_invitation',
            entity_id=str(invitation.pk),
            new_value={
                'email': invitation.email,
                'role': invitation.role,
            },
        )

        messages.success(request, _("Invitation sent to %(email)s.") % {'email': invitation.email})
        return redirect(f'/tournaments/{tournament.slug}/staff/')

    def _send_invitation_email(self, invitation):
        accept_url = self.request.build_absolute_uri(
            f"/tournaments/staff-invitations/{invitation.token}/",
        )
        subject = _("You're invited as %(role)s for %(tournament)s") % {
            'role': invitation.get_role_display(),
            'tournament': invitation.tournament.name,
        }
        body = render_to_string('emails/tournament_staff_invitation.txt', {
            'invitation': invitation,
            'tournament': invitation.tournament,
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
            pass


class TournamentStaffAcceptInvitationView(LoginRequiredMixin, View):
    template_name = 'organizations/workspace/accept_tournament_staff_invitation.html'

    def _get_invitation(self, token):
        return get_object_or_404(TournamentStaffInvitation, token=token)

    def get(self, request, token):
        invitation = self._get_invitation(token)
        context = {
            'invitation': invitation,
            'tournament': invitation.tournament,
            'already_accepted': invitation.is_accepted,
            'expired': invitation.is_expired,
        }
        return render(request, self.template_name, context)

    def post(self, request, token):
        from users.models import UserPermission

        invitation = self._get_invitation(token)
        if invitation.is_accepted:
            messages.info(request, _("This invitation has already been accepted."))
            return redirect('/')

        if invitation.is_expired:
            messages.error(request, _("This invitation has expired. Please ask for a new one."))
            return redirect('/')

        membership, created = TournamentStaffMembership.objects.get_or_create(
            tournament=invitation.tournament,
            user=request.user,
            role=invitation.role,
            defaults={
                'invited_by': invitation.invited_by,
                'accepted_at': timezone.now(),
            },
        )
        if not created and membership.accepted_at is None:
            membership.accepted_at = timezone.now()
            membership.save(update_fields=['accepted_at'])

        role_permissions = _permissions_for_staff_role(invitation.role)
        existing = set(
            UserPermission.objects.filter(
                user=request.user,
                tournament=invitation.tournament,
            ).values_list('permission', flat=True),
        )
        UserPermission.objects.bulk_create([
            UserPermission(
                user=request.user,
                permission=permission,
                tournament=invitation.tournament,
            )
            for permission in role_permissions - existing
        ], ignore_conflicts=True)

        invitation.accepted_at = timezone.now()
        invitation.accepted_by = request.user
        invitation.save(update_fields=['accepted_at', 'accepted_by'])

        TournamentAuditLog.objects.create(
            tournament=invitation.tournament,
            actor=request.user,
            action='tournament.staff.accepted_invite',
            entity_type='tournament_staff_invitation',
            entity_id=str(invitation.pk),
            new_value={
                'role': invitation.role,
                'user_id': request.user.pk,
            },
        )

        messages.success(
            request,
            _("You're now added as %(role)s for %(tournament)s.") % {
                'role': invitation.get_role_display(),
                'tournament': invitation.tournament.name,
            },
        )
        return redirect(f'/tournaments/{invitation.tournament.slug}/')


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


# ─────────────────────────────────────────────────────────────────────────────
# Form system
# ─────────────────────────────────────────────────────────────────────────────

class FormListView(WorkspaceAccessMixin, TemplateView):
    template_name = 'organizations/workspace/forms/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'forms'
        ctx['forms'] = OrgForm.objects.filter(organization=self.organization)
        return ctx


class FormCreateView(WorkspaceAdminMixin, View):
    template_name = 'organizations/workspace/forms/create.html'

    def _ctx(self, **extra):
        return {
            'organization': self.organization,
            'membership': self.membership,
            'active_tab': 'forms',
            'categories': OrgForm.Category.choices,
            'action': 'create',
            **extra,
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._ctx(
            form_obj=None,
            form_fields_json='[]',
        ))

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        slug_val = request.POST.get('slug', '').strip()
        category = request.POST.get('category', OrgForm.Category.OTHER)
        is_accepting = request.POST.get('is_accepting') == '1'
        is_confirmation_public = request.POST.get('is_confirmation_public') == '1'
        fields_json = request.POST.get('fields_json', '[]').strip()

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not slug_val:
            errors['slug'] = 'Slug is required.'
        elif OrgForm.objects.filter(organization=self.organization, slug=slug_val).exists():
            errors['slug'] = 'A form with this slug already exists in this organization.'

        try:
            fields_data = json.loads(fields_json)
            if not isinstance(fields_data, list):
                raise ValueError()
        except (json.JSONDecodeError, ValueError):
            fields_data = []
            errors['fields'] = 'Invalid field data.'

        if errors:
            return render(request, self.template_name, self._ctx(
                form_obj=None,
                errors=errors,
                form_fields_json=fields_json,
                post_name=name,
                post_slug=slug_val,
                post_category=category,
            ))

        form_obj = OrgForm.objects.create(
            organization=self.organization,
            name=name,
            slug=slug_val,
            category=category,
            fields=fields_data,
            is_accepting=is_accepting,
            is_confirmation_public=is_confirmation_public,
        )
        messages.success(request, f'Form "{form_obj.name}" created.')
        return redirect(f'/forms/{form_obj.slug}/responses/')


class FormBuilderView(WorkspaceAdminMixin, View):
    template_name = 'organizations/workspace/forms/create.html'

    def _ctx(self, form_obj, **extra):
        return {
            'organization': self.organization,
            'membership': self.membership,
            'active_tab': 'forms',
            'categories': OrgForm.Category.choices,
            'action': 'edit',
            'form_obj': form_obj,
            **extra,
        }

    def get(self, request, form_slug, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        return render(request, self.template_name, self._ctx(
            form_obj=form_obj,
            form_fields_json=json.dumps(form_obj.fields or []),
        ))

    def post(self, request, form_slug, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        name = request.POST.get('name', '').strip()
        new_slug = request.POST.get('slug', '').strip()
        category = request.POST.get('category', form_obj.category)
        is_accepting = request.POST.get('is_accepting') == '1'
        is_confirmation_public = request.POST.get('is_confirmation_public') == '1'
        fields_json = request.POST.get('fields_json', '[]').strip()

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not new_slug:
            errors['slug'] = 'Slug is required.'
        elif (new_slug != form_obj.slug and
              OrgForm.objects.filter(organization=self.organization, slug=new_slug).exists()):
            errors['slug'] = 'A form with this slug already exists in this organization.'

        try:
            fields_data = json.loads(fields_json)
            if not isinstance(fields_data, list):
                raise ValueError()
        except (json.JSONDecodeError, ValueError):
            fields_data = form_obj.fields
            errors['fields'] = 'Invalid field data.'

        if errors:
            return render(request, self.template_name, self._ctx(
                form_obj=form_obj,
                errors=errors,
                form_fields_json=fields_json,
            ))

        form_obj.name = name
        form_obj.slug = new_slug
        form_obj.category = category
        form_obj.fields = fields_data
        form_obj.is_accepting = is_accepting
        form_obj.is_confirmation_public = is_confirmation_public
        form_obj.save()
        messages.success(request, f'Form "{form_obj.name}" updated.')
        return redirect(f'/forms/{form_obj.slug}/responses/')


class FormResponseListView(WorkspaceAccessMixin, View):
    template_name = 'organizations/workspace/forms/responses.html'

    def get(self, request, form_slug, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        status_filter = request.GET.get('status', 'all')
        qs = form_obj.responses.all()
        if status_filter == 'pending':
            qs = qs.filter(status=OrgFormResponse.Status.PENDING)
        elif status_filter == 'confirmed':
            qs = qs.filter(status=OrgFormResponse.Status.CONFIRMED)

        responses = list(qs)  # evaluate once for both context and JSON serialization
        field_defs = form_obj.fields or []
        resp_data_json = json.dumps({str(r.pk): r.data for r in responses})
        field_defs_json = json.dumps(field_defs)

        return render(request, self.template_name, {
            'organization': self.organization,
            'membership': self.membership,
            'active_tab': 'forms',
            'form_obj': form_obj,
            'responses': responses,
            'status_filter': status_filter,
            'field_defs': field_defs,
            'resp_data_json': resp_data_json,
            'field_defs_json': field_defs_json,
            'pending_count': form_obj.responses.filter(status=OrgFormResponse.Status.PENDING).count(),
            'confirmed_count': form_obj.responses.filter(status=OrgFormResponse.Status.CONFIRMED).count(),
            'total_count': form_obj.responses.count(),
        })


class FormConfirmView(WorkspaceAdminMixin, View):
    def post(self, request, form_slug, response_id, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        resp = get_object_or_404(OrgFormResponse, form=form_obj, pk=response_id)
        try:
            slots = max(1, int(request.POST.get('slots', 1)))
        except (ValueError, TypeError):
            slots = 1
        resp.status = OrgFormResponse.Status.CONFIRMED
        resp.confirmed_slots = slots
        resp.confirmed_at = timezone.now()
        resp.save()
        return redirect(f'/forms/{form_slug}/responses/?status=pending')


class FormUnconfirmView(WorkspaceAdminMixin, View):
    def post(self, request, form_slug, response_id, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        resp = get_object_or_404(OrgFormResponse, form=form_obj, pk=response_id)
        resp.status = OrgFormResponse.Status.PENDING
        resp.confirmed_slots = None
        resp.confirmed_at = None
        resp.save()
        return redirect(f'/forms/{form_slug}/responses/?status=confirmed')


class FormDeleteResponseView(WorkspaceAdminMixin, View):
    def post(self, request, form_slug, response_id, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        resp = get_object_or_404(OrgFormResponse, form=form_obj, pk=response_id)
        resp.delete()
        messages.success(request, 'Response deleted.')
        return redirect(f'/forms/{form_slug}/responses/')


class FormDeleteView(WorkspaceAdminMixin, View):
    def post(self, request, form_slug, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        name = form_obj.name
        form_obj.delete()
        messages.success(request, f'Form "{name}" deleted.')
        return redirect('/forms/')


class FormToggleView(WorkspaceAdminMixin, View):
    """Toggle is_accepting or is_confirmation_public without a full page save."""

    def post(self, request, form_slug, *args, **kwargs):
        form_obj = get_object_or_404(OrgForm, organization=self.organization, slug=form_slug)
        field = request.POST.get('field')
        if field == 'accepting':
            form_obj.is_accepting = not form_obj.is_accepting
            form_obj.save(update_fields=['is_accepting', 'updated_at'])
        elif field == 'confirmation_public':
            form_obj.is_confirmation_public = not form_obj.is_confirmation_public
            form_obj.save(update_fields=['is_confirmation_public', 'updated_at'])
        return redirect(f'/forms/{form_slug}/responses/')


# ---- Public views (no authentication required) ----

class PublicFormSubmissionView(View):
    """Public form submission page — accessible without login."""

    template_name = 'organizations/workspace/forms/public_submit.html'

    def _resolve(self, request, form_slug):
        org = getattr(request, 'tenant_organization', None)
        if not org:
            raise Http404
        return org, get_object_or_404(OrgForm, organization=org, slug=form_slug)

    def get(self, request, form_slug, *args, **kwargs):
        org, form_obj = self._resolve(request, form_slug)
        return render(request, self.template_name, {'organization': org, 'form_obj': form_obj})

    def post(self, request, form_slug, *args, **kwargs):
        org, form_obj = self._resolve(request, form_slug)
        if not form_obj.is_accepting:
            return render(request, self.template_name, {
                'organization': org, 'form_obj': form_obj, 'not_accepting': True,
            })

        data = {}
        for field in (form_obj.fields or []):
            fid = field.get('id', '')
            ftype = field.get('type', 'text')
            if ftype == 'multiselect':
                data[fid] = request.POST.getlist(f'field_{fid}')
            elif ftype == 'checkbox':
                data[fid] = f'field_{fid}' in request.POST
            else:
                data[fid] = request.POST.get(f'field_{fid}', '').strip()

        OrgFormResponse.objects.create(form=form_obj, data=data)
        return render(request, self.template_name, {
            'organization': org, 'form_obj': form_obj, 'submitted': True,
        })


class PublicFormConfirmationBoardView(View):
    """Public read-only confirmed-slots board."""

    template_name = 'organizations/workspace/forms/public_confirmed.html'

    def get(self, request, form_slug, *args, **kwargs):
        org = getattr(request, 'tenant_organization', None)
        if not org:
            raise Http404
        form_obj = get_object_or_404(OrgForm, organization=org, slug=form_slug)
        confirmed = form_obj.responses.filter(
            status=OrgFormResponse.Status.CONFIRMED,
        ).order_by('confirmed_at')
        return render(request, self.template_name, {
            'organization': org,
            'form_obj': form_obj,
            'confirmed_responses': confirmed,
        })
