from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.template import loader
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from users.permissions import Permission

from .forms import WorkspaceTournamentCreateForm
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
        ctx['members'] = self.organization.memberships.select_related('user').order_by('role')
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
