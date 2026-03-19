import csv
import io
import json

from django.conf import settings as django_settings
from django.http import Http404, JsonResponse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from jose import JWTError, jwt

from participants.models import Adjudicator, Institution, Speaker, Team
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
        t = self.tournament
        kwargs['tournament_slug'] = t.slug
        kwargs['tournament_id'] = t.id
        kwargs['api_base_url'] = '/api/ie/'
        kwargs['nekospeech_url'] = django_settings.NEKOSPEECH_URL
        kwargs['nekospeech_api_key'] = django_settings.NEKOSPEECH_IE_API_KEY
        kwargs['has_ie_events'] = True
        kwargs['ie_token'] = issue_ie_token(self.request.user, role='director')
        kwargs['full_width_layout'] = True
        kwargs['speaker_count'] = Speaker.objects.filter(team__tournament=t).count()
        kwargs['judge_count'] = Adjudicator.objects.filter(tournament=t).count()
        kwargs['institution_count'] = Institution.objects.filter(
            team__tournament=t).distinct().count()
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


# ---------------------------------------------------------------------------
# Tournament Prep — Participant Management (Django models)
# ---------------------------------------------------------------------------

class IETournamentPrepView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'speech_events/ie_prep.html'
    page_title = _("Tournament Prep — Participants")
    page_emoji = '🎤'
    edit_permission = Permission.EDIT_SETTINGS

    def get_context_data(self, **kwargs):
        kwargs['tournament_slug'] = self.tournament.slug
        kwargs['tournament_id'] = self.tournament.id
        kwargs['full_width_layout'] = True
        return super().get_context_data(**kwargs)


def _serialize_institution(inst):
    return {'id': inst.id, 'name': inst.name, 'code': inst.code}


def _serialize_speaker(spk):
    inst = spk.team.institution
    return {
        'id': spk.person_ptr_id,
        'name': spk.name,
        'email': spk.email or '',
        'institution_code': inst.code if inst else '',
        'institution_name': inst.name if inst else '',
    }


def _serialize_judge(adj):
    return {
        'id': adj.person_ptr_id,
        'name': adj.name,
        'email': adj.email or '',
        'institution_code': adj.institution.code if adj.institution else '',
        'institution_name': adj.institution.name if adj.institution else '',
    }


class IEPrepAllView(AdministratorMixin, TournamentMixin, View):
    """Return all institutions, speakers, and judges for this tournament."""
    edit_permission = Permission.EDIT_SETTINGS

    def get(self, request, *args, **kwargs):
        t = self.tournament
        # Show all institutions in the system — the user will pick from these
        # when adding speakers/judges. Includes institutions from other
        # tournaments too, since schools are shared resources.
        all_institutions = Institution.objects.all().order_by('name')

        speakers = Speaker.objects.filter(
            team__tournament=t
        ).select_related('team__institution').order_by('name')

        judges = Adjudicator.objects.filter(
            tournament=t
        ).select_related('institution').order_by('name')

        return JsonResponse({
            'institutions': [_serialize_institution(i) for i in all_institutions],
            'speakers': [_serialize_speaker(s) for s in speakers],
            'judges': [_serialize_judge(j) for j in judges],
        })


class IEPrepInstitutionsView(AdministratorMixin, TournamentMixin, View):
    """Create / delete institutions."""
    edit_permission = Permission.EDIT_SETTINGS

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = (data.get('name') or '').strip()[:100]
        code = (data.get('code') or '').strip()[:20]
        if not name or not code:
            return JsonResponse({'error': 'Name and code are required.'}, status=400)

        inst, created = Institution.objects.get_or_create(
            name=name, code=code,
        )
        if not created:
            return JsonResponse(_serialize_institution(inst))
        return JsonResponse(_serialize_institution(inst), status=201)

    def delete(self, request, *args, **kwargs):
        inst_id = self.kwargs.get('inst_id')
        try:
            inst = Institution.objects.get(id=inst_id)
        except Institution.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        # Check if any speakers or adjudicators reference it in this tournament
        has_speakers = Speaker.objects.filter(
            team__tournament=self.tournament, team__institution=inst).exists()
        has_judges = Adjudicator.objects.filter(
            tournament=self.tournament, institution=inst).exists()
        if has_speakers or has_judges:
            return JsonResponse({
                'error': 'Cannot delete — this school has speakers or judges assigned. Remove them first.'
            }, status=409)
        # Check if any other entity references it before deleting
        has_any_teams = Team.objects.filter(institution=inst).exists()
        has_any_adjs = Adjudicator.objects.filter(institution=inst).exists()
        if has_any_teams or has_any_adjs:
            # Don't delete — used by other tournaments
            return JsonResponse({}, status=204)
        inst.delete()
        return JsonResponse({}, status=204)


class IEPrepSpeakersView(AdministratorMixin, TournamentMixin, View):
    """Create / delete speakers (with auto-created teams)."""
    edit_permission = Permission.EDIT_SETTINGS

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = (data.get('name') or '').strip()[:70]
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)

        institution_id = data.get('institution_id')
        institution = None
        if institution_id:
            try:
                institution = Institution.objects.get(id=institution_id)
            except Institution.DoesNotExist:
                return JsonResponse({'error': 'Institution not found.'}, status=400)

        email = (data.get('email') or '').strip()[:254] or None

        # For IE: create one team per speaker
        team = Team(
            tournament=self.tournament,
            institution=institution,
            reference=name,
            short_reference=name[:35],
            use_institution_prefix=False,
        )
        team.save()

        speaker = Speaker.objects.create(
            name=name,
            team=team,
            email=email,
        )
        return JsonResponse(_serialize_speaker(speaker), status=201)

    def delete(self, request, *args, **kwargs):
        spk_id = self.kwargs.get('spk_id')
        try:
            speaker = Speaker.objects.select_related('team').get(
                person_ptr_id=spk_id, team__tournament=self.tournament)
        except Speaker.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        team = speaker.team
        speaker.delete()
        # Also delete the auto-created single-speaker team
        if not team.speaker_set.exists():
            team.delete()
        return JsonResponse({}, status=204)


class IEPrepJudgesView(AdministratorMixin, TournamentMixin, View):
    """Create / delete adjudicators."""
    edit_permission = Permission.EDIT_SETTINGS

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = (data.get('name') or '').strip()[:70]
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)

        institution_id = data.get('institution_id')
        institution = None
        if institution_id:
            try:
                institution = Institution.objects.get(id=institution_id)
            except Institution.DoesNotExist:
                return JsonResponse({'error': 'Institution not found.'}, status=400)

        email = (data.get('email') or '').strip()[:254] or None

        adj = Adjudicator.objects.create(
            name=name,
            tournament=self.tournament,
            institution=institution,
            email=email,
            base_score=0,
        )
        return JsonResponse(_serialize_judge(adj), status=201)

    def delete(self, request, *args, **kwargs):
        adj_id = self.kwargs.get('adj_id')
        try:
            adj = Adjudicator.objects.get(
                person_ptr_id=adj_id, tournament=self.tournament)
        except Adjudicator.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        adj.delete()
        return JsonResponse({}, status=204)


class IEPrepImportView(AdministratorMixin, TournamentMixin, View):
    """CSV import for institutions, speakers, or judges."""
    edit_permission = Permission.EDIT_SETTINGS

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        import_type = data.get('type')
        csv_text = data.get('csv', '').strip()
        if not csv_text:
            return JsonResponse({'error': 'No CSV data provided.'}, status=400)
        if import_type not in ('institutions', 'speakers', 'judges'):
            return JsonResponse({'error': 'Invalid import type.'}, status=400)

        reader = csv.reader(io.StringIO(csv_text))
        rows = [r for r in reader if any(cell.strip() for cell in r)]

        if not rows:
            return JsonResponse({'error': 'No data rows found.'}, status=400)

        if import_type == 'institutions':
            return self._import_institutions(rows)
        elif import_type == 'speakers':
            return self._import_speakers(rows)
        elif import_type == 'judges':
            return self._import_judges(rows)

    def _import_institutions(self, rows):
        created = 0
        skipped = 0
        for row in rows:
            if len(row) < 2:
                skipped += 1
                continue
            name = row[0].strip()[:100]
            code = row[1].strip()[:20]
            if not name or not code:
                skipped += 1
                continue
            _, was_created = Institution.objects.get_or_create(name=name, code=code)
            if was_created:
                created += 1
            else:
                skipped += 1
        return JsonResponse({
            'message': f'Imported {created} schools ({skipped} skipped/duplicates).'
        })

    def _import_speakers(self, rows):
        # Build institution lookup
        inst_map = {}
        for inst in Institution.objects.all():
            inst_map[inst.code.upper()] = inst

        created = 0
        errors = []
        for i, row in enumerate(rows):
            name = row[0].strip()[:70] if len(row) > 0 else ''
            inst_code = row[1].strip().upper() if len(row) > 1 else ''
            email = row[2].strip()[:254] if len(row) > 2 else ''
            if not name:
                errors.append(f'Row {i+1}: missing name')
                continue
            institution = inst_map.get(inst_code) if inst_code else None
            if inst_code and institution is None:
                errors.append(f'Row {i+1}: unknown school code "{row[1].strip()}"')
                continue

            team = Team(
                tournament=self.tournament,
                institution=institution,
                reference=name,
                short_reference=name[:35],
                use_institution_prefix=False,
            )
            team.save()
            Speaker.objects.create(name=name, team=team, email=email or None)
            created += 1

        msg = f'Imported {created} speakers.'
        if errors:
            msg += f' {len(errors)} errors: ' + '; '.join(errors[:5])
        return JsonResponse({'message': msg})

    def _import_judges(self, rows):
        inst_map = {}
        for inst in Institution.objects.all():
            inst_map[inst.code.upper()] = inst

        created = 0
        errors = []
        for i, row in enumerate(rows):
            name = row[0].strip()[:70] if len(row) > 0 else ''
            inst_code = row[1].strip().upper() if len(row) > 1 else ''
            email = row[2].strip()[:254] if len(row) > 2 else ''
            if not name:
                errors.append(f'Row {i+1}: missing name')
                continue
            institution = inst_map.get(inst_code) if inst_code else None

            Adjudicator.objects.create(
                name=name,
                tournament=self.tournament,
                institution=institution,
                email=email or None,
                base_score=0,
            )
            created += 1

        msg = f'Imported {created} judges.'
        if errors:
            msg += f' {len(errors)} errors: ' + '; '.join(errors[:5])
        return JsonResponse({'message': msg})
