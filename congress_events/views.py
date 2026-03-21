"""Views for the congress_events Django app.

Each view renders a template that mounts a Vue component communicating
with the nekocongress FastAPI microservice.
"""

from django.conf import settings as django_settings
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from tournaments.mixins import TournamentMixin
from users.permissions import Permission
from utils.mixins import AdministratorMixin

from congress_events.jwt_utils import issue_congress_token
from participants.models import Adjudicator, Speaker


class CongressDashboardView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_dashboard.html'
    page_title = _("Congressional Debate")
    page_emoji = '🏛️'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        kwargs['speaker_count'] = Speaker.objects.filter(team__tournament=t).count()
        kwargs['judge_count'] = Adjudicator.objects.filter(tournament=t).count()
        return super().get_context_data(**kwargs)


class CongressSetupView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_setup.html'
    page_title = _("Congress Setup Wizard")
    page_emoji = '🏛️'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressDocketView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_docket.html'
    page_title = _("Docket Management")
    page_emoji = '📜'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressChamberView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_chamber.html'
    page_title = _("Chamber Management")
    page_emoji = '🏛️'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressSessionView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_session.html'
    page_title = _("Live Session Floor")
    page_emoji = '🎙️'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        session_id = self.kwargs.get('session_id', 0)
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['session_id'] = session_id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressScorerView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_scorer.html'
    page_title = _("Scorer Ballot")
    page_emoji = '📋'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        session_id = self.kwargs.get('session_id', 0)
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['session_id'] = session_id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='judge', tournament_id=t.id)
        kwargs['judge_id'] = self.request.user.pk
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressStandingsView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'congress_events/congress_standings.html'
    page_title = _("Congress Standings")
    page_emoji = '🏆'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='director', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressStudentView(TournamentMixin, TemplateView):
    """Public student-facing view — no admin required."""
    template_name = 'congress_events/congress_student.html'
    page_title = _("Student Session View")
    page_emoji = '📖'

    def get_context_data(self, **kwargs):
        t = self.tournament
        session_id = self.kwargs.get('session_id', 0)
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['session_id'] = session_id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='student', tournament_id=t.id)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class CongressPOView(TournamentMixin, TemplateView):
    """PO-facing view for presiding over a session."""
    template_name = 'congress_events/congress_po.html'
    page_title = _("Presiding Officer Panel")
    page_emoji = '⚖️'

    def get_context_data(self, **kwargs):
        t = self.tournament
        session_id = self.kwargs.get('session_id', 0)
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['session_id'] = session_id
        kwargs['nekocongress_url'] = getattr(django_settings, 'NEKOCONGRESS_URL', '')
        kwargs['nekocongress_api_key'] = getattr(django_settings, 'NEKOCONGRESS_API_KEY', '')
        kwargs['congress_token'] = issue_congress_token(
            self.request.user, role='po', tournament_id=t.id)
        kwargs['judge_id'] = self.request.user.pk
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)
