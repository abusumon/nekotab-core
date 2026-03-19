from django.conf import settings as django_settings
from django.http import Http404, JsonResponse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from jose import JWTError, jwt

from tournaments.mixins import PublicTournamentPageMixin, TournamentMixin
from users.permissions import Permission
from utils.mixins import AdministratorMixin

from speech_events.jwt_utils import issue_ie_token, issue_judge_ballot_token


class IEDashboardView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_dashboard.html'
    page_title = _("Individual Events")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['has_ie_events'] = True
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IESetupView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_setup.html'
    page_title = _("IE Setup Wizard")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        from utils.misc import subdomain_reverse_tournament
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['dashboard_url'] = subdomain_reverse_tournament(
            'ie-admin-dashboard', self.tournament)
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IEEntryManagerView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_entries.html'
    page_title = _("IE Entries")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        event_id = self.kwargs['event_id']
        # Fetch event name/type from nekospeech
        event_name = ''
        event_type = ''
        num_rounds = 3
        try:
            import json
            import urllib.request
            nekospeech_url = django_settings.NEKOSPEECH_URL.rstrip('/')
            headers = {}
            api_key = django_settings.NEKOSPEECH_IE_API_KEY
            if api_key:
                headers["X-IE-Api-Key"] = api_key
            req = urllib.request.Request(
                f"{nekospeech_url}/events/{event_id}/", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                event_name = data.get('name', '')
                event_type = data.get('event_type', '')
                num_rounds = data.get('num_rounds', 3)
        except Exception:
            pass

        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = event_id
        kwargs['event_name'] = event_name
        kwargs['event_type'] = event_type
        kwargs['num_rounds'] = num_rounds
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IEFinalistsView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_finalists.html'
    page_title = _("IE Finals")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        event_id = self.kwargs['event_id']
        num_rounds = 3
        try:
            import json
            import urllib.request
            nekospeech_url = django_settings.NEKOSPEECH_URL.rstrip('/')
            headers = {}
            api_key = django_settings.NEKOSPEECH_IE_API_KEY
            if api_key:
                headers["X-IE-Api-Key"] = api_key
            req = urllib.request.Request(
                f"{nekospeech_url}/events/{event_id}/", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                num_rounds = data.get('num_rounds', 3)
        except Exception:
            pass

        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = event_id
        kwargs['num_rounds'] = num_rounds
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IEJudgeLinksPageView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_judge_links.html'
    page_title = _("IE Judge Links")
    page_emoji = '🎤'
    edit_permission = Permission.RELEASE_DRAW

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['round_number'] = self.kwargs['round_number']
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IERoomDrawView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_draw.html'
    page_title = _("IE Room Draw")
    page_emoji = '🎤'
    edit_permission = Permission.RELEASE_DRAW

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['round_number'] = self.kwargs['round_number']
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IEBallotView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_ballot.html'
    page_title = _("IE Ballot")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_BALLOTSUBMISSIONS

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['room_id'] = self.kwargs['room_id']
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


class IEPublicDashboardView(PublicTournamentPageMixin, TemplateView):
    template_name = 'speech_events/ie_public.html'
    public_page_preference = 'public_results'
    page_title = _("Individual Events")
    page_emoji = '🎤'

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['has_ie_events'] = True
        return super().get_context_data(**kwargs)


class IEStandingsView(PublicTournamentPageMixin, TemplateView):
    template_name = 'speech_events/ie_standings.html'
    public_page_preference = 'public_results'
    page_title = _("IE Standings")
    page_emoji = '🎤'

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = self.kwargs.get('event_id', 0)
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        return super().get_context_data(**kwargs)


class IEAdminStandingsView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_standings.html'
    page_title = _("IE Standings")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


# ---------------------------------------------------------------------------
# Judge Ballot Access (no login required — token-based)
# ---------------------------------------------------------------------------

class IEJudgeBallotView(TournamentMixin, TemplateView):
    """Serve the ballot page for a judge using a signed token URL.

    URL: /<tournament>/ie/judge-ballot/<token>/
    No login required — the token IS the authentication.
    Token carries: judge_id, room_id, event_id, tournament_id, role=judge.
    """
    template_name = 'speech_events/ie_ballot.html'
    page_title = _("IE Ballot — Judge")
    page_emoji = '🎤'

    def get_context_data(self, **kwargs):
        token = self.kwargs['token']

        # Validate the token
        try:
            payload = jwt.decode(
                token, django_settings.SECRET_KEY, algorithms=["HS256"]
            )
        except JWTError:
            raise Http404(_("Invalid or expired ballot link."))

        # Verify token is for this tournament
        if payload.get('tournament_id') != self.tournament.id:
            raise Http404(_("Invalid ballot link for this tournament."))

        if payload.get('role') != 'judge':
            raise Http404(_("Invalid ballot link."))

        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['event_id'] = payload['event_id']
        kwargs['room_id'] = payload['room_id']
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        # Pass the same token as the API bearer token
        kwargs['ie_token'] = token
        kwargs['is_judge'] = True
        return super().get_context_data(**kwargs)


class IEGenerateJudgeLinksView(AdministratorMixin, TournamentMixin, View):
    """Generate tokenized ballot URLs for all judges in a round.

    POST /<tournament>/admin/ie/<event_id>/judge-links/<round_number>/
    Returns JSON with judge_id → ballot_url mapping.
    """
    edit_permission = Permission.RELEASE_DRAW

    def post(self, request, *args, **kwargs):
        import json
        import urllib.request
        event_id = self.kwargs['event_id']
        round_number = self.kwargs['round_number']

        # Fetch the draw from nekospeech to get room → judge assignments
        nekospeech_url = django_settings.NEKOSPEECH_URL.rstrip('/')
        draw_url = f"{nekospeech_url}/draw/{event_id}/round/{round_number}/"

        try:
            headers = {}
            api_key = django_settings.NEKOSPEECH_IE_API_KEY
            if api_key:
                headers["X-IE-Api-Key"] = api_key
            req = urllib.request.Request(draw_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                draw_data = json.loads(resp.read())
        except Exception:
            return JsonResponse({"error": "Failed to fetch draw from nekospeech"}, status=502)

        base_url = request.build_absolute_uri(f'/{self.tournament.slug}/ie/judge-ballot/')
        links = []

        for room in draw_data.get('rooms', []):
            if not room.get('judge_id'):
                continue
            ballot_token = issue_judge_ballot_token(
                judge_id=room['judge_id'],
                room_id=room['id'],
                event_id=event_id,
                tournament_id=self.tournament.id,
            )
            links.append({
                'judge_id': room['judge_id'],
                'judge_name': room.get('judge_name', ''),
                'room_number': room['room_number'],
                'room_id': room['id'],
                'ballot_url': f"{base_url}{ballot_token}/",
            })

        return JsonResponse({'links': links})
