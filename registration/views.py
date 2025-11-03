from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms import SimpleArrayField
from django.db.models import Count, Prefetch, Sum
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, gettext_lazy, ngettext
from django.views.generic.edit import CreateView, FormView
from formtools.wizard.views import SessionWizardView

from actionlog.mixins import LogActionMixin
from actionlog.models import ActionLogEntry
from participants.emoji import EMOJI_NAMES
from participants.models import Adjudicator, Coach, Speaker, Team, TournamentInstitution
from tournaments.mixins import PublicTournamentPageMixin, TournamentMixin
from users.permissions import Permission
from utils.misc import reverse_tournament
from utils.mixins import AdministratorMixin
from utils.tables import TabbycatTableBuilder
from utils.views import ModelFormSetView, VueTableTemplateView

from .forms import AdjudicatorForm, InstitutionCoachForm, ParticipantAllocationForm, SpeakerForm, TeamForm, TournamentInstitutionForm
from .models import Invitation, Question
from .utils import populate_invitation_url_keys


class CustomQuestionFormMixin:

    def get_form_kwargs(self, step=None):
        if step is not None:
            kwargs = super().get_form_kwargs(step)
        else:
            kwargs = super().get_form_kwargs()
        kwargs['tournament'] = self.tournament
        return kwargs


class InstitutionalRegistrationMixin:

    def get_institution(self):
        ti = TournamentInstitution.objects.filter(tournament=self.tournament, coach__url_key=self.kwargs['url_key']).select_related('institution')
        return get_object_or_404(ti).institution

    @property
    def institution(self):
        if not hasattr(self, '_institution'):
            self._institution = self.get_institution()
        return self._institution

    def get_form_kwargs(self, step=None):
        if step is not None:
            kwargs = super().get_form_kwargs(step)
        else:
            kwargs = super().get_form_kwargs()
        kwargs['institution'] = self.institution
        return kwargs

    def get_success_url(self):
        return reverse_tournament('reg-inst-landing', self.tournament, kwargs={'url_key': self.kwargs['url_key']})


class CreateInstitutionFormView(LogActionMixin, PublicTournamentPageMixin, CustomQuestionFormMixin, SessionWizardView):
    form_list = [
        ('institution', TournamentInstitutionForm),
        ('coach', InstitutionCoachForm),
    ]
    template_name = 'institution_registration_form.html'
    page_emoji = '🏫'
    page_title = gettext_lazy("Register Institution")

    public_page_preference = 'institution_registration'
    action_log_type = ActionLogEntry.ActionType.INSTITUTION_REGISTER

    def get_success_url(self, coach):
        return reverse_tournament('reg-inst-landing', self.tournament, kwargs={'url_key': coach.url_key})

    def done(self, form_list, form_dict, **kwargs):
        t_inst = form_dict['institution'].save()
        self.object = t_inst

        coach_form = form_dict['coach']
        coach_form.instance.tournament_institution = t_inst
        coach = coach_form.save()

        invitations = [
            Invitation(tournament=self.tournament, institution=t_inst.institution, for_content_type=ContentType.objects.get_for_model(Adjudicator)),
            Invitation(tournament=self.tournament, institution=t_inst.institution, for_content_type=ContentType.objects.get_for_model(Team)),
        ]
        populate_invitation_url_keys(invitations, self.tournament)
        Invitation.objects.bulk_create(invitations)

        messages.success(self.request, _("Your institution %s has been registered!") % t_inst.institution.name)
        self.log_action()
        return HttpResponseRedirect(self.get_success_url(coach))


class BaseCreateTeamFormView(LogActionMixin, PublicTournamentPageMixin, CustomQuestionFormMixin, SessionWizardView):
    form_list = [
        ('team', TeamForm),
        ('speaker', modelformset_factory(Speaker, form=SpeakerForm, extra=0)),
    ]
    template_name = 'team_registration_form.html'
    page_emoji = '👯'

    public_page_preference = 'open_team_registration'
    action_log_type = ActionLogEntry.ActionType.TEAM_REGISTER

    REFERENCE_GENERATORS = {
        'user': '_custom_reference',
        'alphabetical': '_alphabetical_reference',
        'numerical': '_numerical_reference',
        'initials': '_initials_reference',
    }

    CODE_NAME_GENERATORS = {
        'user': '_custom_code_name',
        'emoji': '_emoji_code_name',
        'last_names': '_last_names_code_name',
    }

    def get_template_names(self):
        if self.steps.current != 'speaker':
            return 'wizard_registration_form.html'
        return 'team_wizard_speakers.html'

    def get_page_title(self):
        match self.steps.current:
            case 'team':
                return _("Register Team")
            case 'speaker':
                return ngettext('Register Speaker', 'Register Speakers', self.tournament.pref('speakers_in_team'))
        return ''

    def get_team_form(self):
        form = self.get_form(
            self.steps.first,
            data=self.storage.get_step_data(self.steps.first),
        )
        team = form.instance
        team.tournament = self.tournament
        team.institution = self.institution
        team.reference = getattr(self, self.REFERENCE_GENERATORS[self.tournament.pref('team_name_generator')])(team, [])
        return form

    def get_page_subtitle(self):
        if self.steps.current == 'team' and hasattr(self, 'institution') and self.institution:
            return _("from %s") % self.institution.name
        elif self.steps.current == 'speaker':
            team_form = self.get_team_form()
            if team_form.is_valid():
                return _("for %s") % team_form.instance._construct_short_name()
        return ''

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == 'speaker':
            kwargs.update({'queryset': self.get_speaker_queryset(), 'form_kwargs': {'team': self.get_team_form().instance}})
            kwargs.pop('tournament')
        return kwargs

    def get_speaker_queryset(self):
        return Speaker.objects.none()

    def get_success_url(self):
        return reverse_tournament('tournament-public-index', self.tournament)

    def get_form(self, step=None, data=None, files=None):
        form = super().get_form(step, data, files)

        if step == 'speaker':
            form.extra = self.tournament.pref('speakers_in_team')
            form.max_num = self.tournament.pref('speakers_in_team')
        return form

    def done(self, form_list, form_dict, **kwargs):
        if self.tournament.pref('team_name_generator') != 'user':
            reference = getattr(self, self.REFERENCE_GENERATORS[self.tournament.pref('team_name_generator')])(form_dict['team'].instance, form_dict['speaker'])
            form_dict['team'].instance.reference = reference

        form_dict['team'].instance.code_name = getattr(self, self.CODE_NAME_GENERATORS[self.tournament.pref('code_name_generator')])(form_dict['team'].instance, form_dict['speaker'])
        team = form_dict['team'].save()
        self.object = team

        for speaker in form_dict['speaker']:
            speaker.team = team
        self.speakers = form_dict['speaker'].save()

        if len(self.speakers) < self.tournament.pref('speakers_in_team'):
            invitation = Invitation(tournament=self.tournament, for_content_type=ContentType.objects.get_for_model(Speaker), team=team)
            populate_invitation_url_keys([invitation], self.tournament)
            invitation.save()

            invite_url = self.request.build_absolute_uri(
                reverse_tournament('reg-create-speaker', self.tournament, kwargs={'pk': team.pk}) + '?key=%s' % invitation.url_key,
                # replace with query={'key': invitation.url_key} in Django 5.2
            )
            messages.warning(self.request, ngettext(
                "Your team only has %(num)d speaker! Invite the other speakers to register using this link: <a href='%(link)s'>%(link)s</a>",
                "Your team only has %(num)d speakers! Invite the other speakers to register using this link: <a href='%(link)s'>%(link)s</a>",
                len(self.speakers),
            ) % {'num': len(self.speakers), 'link': invite_url})

        messages.success(self.request, _("Your team %s has been registered!") % team.short_name)
        self.log_action()
        return HttpResponseRedirect(self.get_success_url())

    @staticmethod
    def _alphabetical_reference(team, speakers=None):
        teams = team.tournament.team_set.filter(institution=team.institution, reference__regex=r"^[A-Z]+$").values_list('reference', flat=True)
        team_numbers = []
        for existing_team in teams:
            n = 0
            for char in existing_team:
                n = n*26 + (ord(char) - 64)
            team_numbers.append(n)

        ch = ''
        mx = max(team_numbers, default=0) + 1
        while mx > 0:
            ch = chr(mx % 26 + 64) + ch
            mx //= 26

        return ch

    @staticmethod
    def _numerical_reference(team, speakers=None):
        teams = team.tournament.team_set.filter(institution=team.institution, reference__regex=r"^\d+$").values_list('reference', flat=True)
        team_numbers = [int(t) for t in teams]
        return str(max(team_numbers) + 1)

    @staticmethod
    def _initials_reference(team, speakers):
        return "".join(s.instance.last_name[0] for s in speakers)

    @staticmethod
    def _custom_reference(team, speakers=None):
        return team.reference

    @staticmethod
    def _custom_code_name(team, speakers=None):
        return team.code_name

    @staticmethod
    def _emoji_code_name(team, speakers=None):
        return EMOJI_NAMES[team.emoji]

    @staticmethod
    def _last_names_code_name(team, speakers=None):
        return ' & '.join(s.instance.last_name for s in speakers if s.instance.last_name is not None)


class PublicCreateTeamFormView(BaseCreateTeamFormView):

    @property
    def key(self):
        return self.request.GET.get('key') or self.request.POST.get('team-key') or self.request.POST.get('speaker-0-key')

    @property
    def institution(self):
        invitation = Invitation.objects.select_related('institution').filter(
            tournament=self.tournament, for_content_type=ContentType.objects.get_for_model(Team), url_key=self.key).first()
        return getattr(invitation, 'institution', None)

    def is_page_enabled(self, tournament):
        if self.key:
            return (
                tournament.pref('institution_participant_registration') and
                Invitation.objects.filter(tournament=tournament, for_content_type=ContentType.objects.get_for_model(Team), url_key=self.key).count() == 1
            )
        return super().is_page_enabled(tournament)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        kwargs['key'] = self.key
        if step == 'speaker':
            kwargs.pop('key')
            kwargs['form_kwargs']['key'] = self.key
        else:
            kwargs['institution'] = self.institution
        return kwargs


class BaseCreateAdjudicatorFormView(LogActionMixin, PublicTournamentPageMixin, CustomQuestionFormMixin, CreateView):
    form_class = AdjudicatorForm
    template_name = 'adjudicator_registration_form.html'
    page_emoji = '👂'
    page_title = gettext_lazy("Register Adjudicator")

    public_page_preference = 'open_adj_registration'
    action_log_type = ActionLogEntry.ActionType.ADJUDICATOR_REGISTER

    def get_page_subtitle(self):
        if hasattr(self, 'institution'):
            return _("from %s") % self.institution.name
        return ''

    def get_success_url(self):
        return reverse_tournament('privateurls-person-index', self.tournament, kwargs={'url_key': self.object.url_key})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, _("You have been registered as an adjudicator!"))
        return super().form_valid(form)


class PublicCreateAdjudicatorFormView(BaseCreateAdjudicatorFormView):

    @property
    def key(self):
        return self.request.GET.get('key') or self.request.POST.get('key')

    @property
    def institution(self):
        invitation = Invitation.objects.select_related('institution').filter(
            tournament=self.tournament, for_content_type=ContentType.objects.get_for_model(Adjudicator), url_key=self.key).first()
        return getattr(invitation, 'institution', None)

    def is_page_enabled(self, tournament):
        if self.key:
            return (
                tournament.pref('institution_participant_registration') and
                Invitation.objects.filter(tournament=tournament, for_content_type=ContentType.objects.get_for_model(Adjudicator), url_key=self.key).count() == 1
            )
        return super().is_page_enabled(tournament)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        invitation = Invitation.objects.select_related('institution').filter(
            tournament=self.tournament, for_content_type=ContentType.objects.get_for_model(Adjudicator), url_key=self.key).first()
        if invitation:
            kwargs['institution'] = invitation.institution
            kwargs['key'] = self.key
        return kwargs


class CreateSpeakerFormView(LogActionMixin, PublicTournamentPageMixin, CustomQuestionFormMixin, CreateView):
    form_class = SpeakerForm
    template_name = 'adjudicator_registration_form.html'
    page_emoji = '👄'
    page_title = gettext_lazy("Register Speaker")
    action_log_type = ActionLogEntry.ActionType.SPEAKER_REGISTER

    @property
    def team(self):
        return self.tournament.team_set.get(pk=self.kwargs['pk'])

    @property
    def key(self):
        return self.request.GET.get('key') or self.request.POST.get('key')

    def get_page_subtitle(self):
        return "for %s" % self.team.short_name

    def is_page_enabled(self, tournament):
        if self.key:
            team = tournament.team_set.prefetch_related('speaker_set').filter(pk=self.kwargs['pk']).first()
            return (
                tournament.pref('institution_participant_registration') and
                Invitation.objects.filter(tournament=tournament, for_content_type=ContentType.objects.get_for_model(Speaker), team=team, url_key=self.key).count() == 1 and
                team.speaker_set.count() < tournament.pref('speakers_in_team')
            )
        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['team'] = self.team
        kwargs['key'] = self.key
        return kwargs

    def get_success_url(self):
        return reverse_tournament('privateurls-person-index', self.tournament, kwargs={'url_key': self.object.url_key})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, _("You have been registered as a speaker!"))

        team = self.object.team
        speakers = team.speaker_set.all()
        if self.tournament.pref('team_name_generator') == 'initials':
            team.reference = BaseCreateTeamFormView._initials_reference(team, speakers)
        if self.tournament.pref('code_name_generator') == 'last_names':
            team.code_name = BaseCreateTeamFormView._last_names_code_name(team, speakers)
        team.save()
        return super().form_valid(form)


class InstitutionalLandingPageView(TournamentMixin, InstitutionalRegistrationMixin, VueTableTemplateView):

    template_name = 'coach_private_url.html'

    def get_adj_table(self):
        adjudicators = self.tournament.adjudicator_set.filter(institution=self.institution)

        table = TabbycatTableBuilder(view=self, title=_('Adjudicators'), sort_key='name')
        table.add_adjudicator_columns(adjudicators, show_institutions=False, show_metadata=False)

        return table

    def get_team_table(self):
        teams = self.tournament.team_set.filter(institution=self.institution)
        table = TabbycatTableBuilder(view=self, title=_('Teams'), sort_key='name')
        table.add_team_columns(teams)

        return table

    def get_tables(self):
        return [self.get_adj_table(), self.get_team_table()]

    def get_context_data(self, **kwargs):
        kwargs["coach"] = get_object_or_404(Coach, tournament_institution__tournament=self.tournament, url_key=kwargs['url_key'])
        kwargs["institution"] = self.institution

        invitations = Invitation.objects.filter(tournament=self.tournament, institution=self.institution).select_related('for_content_type')
        for invitation in invitations:
            kwargs['%s_invitation_link' % invitation.for_content_type.model] = self.request.build_absolute_uri(
                reverse_tournament('reg-create-%s' % invitation.for_content_type.model, self.tournament) + '?key=%s' % invitation.url_key,
                # replace with query={'key': invitation.url_key} in Django 5.2
            )
        return super().get_context_data(**kwargs)


class InstitutionalCreateTeamFormView(InstitutionalRegistrationMixin, BaseCreateTeamFormView):

    public_page_preference = 'institution_participant_registration'

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == 'speaker':
            kwargs.pop('institution')
        return kwargs


class InstitutionalCreateAdjudicatorFormView(InstitutionalRegistrationMixin, BaseCreateAdjudicatorFormView):
    public_page_preference = 'institution_participant_registration'


def handle_question_columns(table: TabbycatTableBuilder, objects, questions=None, suffix=0) -> None:
    if questions is None:
        questions = table.tournament.question_set.filter(for_content_type=ContentType.objects.get_for_model(objects.model)).order_by('seq')
    question_columns = {q: [] for q in questions}

    for obj in objects:
        obj_answers = {answer.question: answer.answer for answer in obj.answers.all()}
        for question, answers in question_columns.items():
            answers.append(obj_answers.get(question, ''))

    for question, answers in question_columns.items():
        table.add_column({'key': f'cq-{question.pk}-{suffix}', 'title': question.name}, answers)


class InstitutionRegistrationTableView(TournamentMixin, AdministratorMixin, VueTableTemplateView, FormView):
    form_class = ParticipantAllocationForm
    page_emoji = '🏫'
    page_title = gettext_lazy("Institutional Registration")
    template_name = 'answer_tables/institutions.html'

    view_permission = Permission.VIEW_REGISTRATION

    def get_table(self):
        t_institutions = self.tournament.tournamentinstitution_set.select_related('institution').prefetch_related(
            'answers__question',
        ).all()

        inst_team_count = {i.id: i.agg for i in self.tournament.tournamentinstitution_set.annotate(agg=Count('institution__team')).all()}
        inst_adj_count = {i.id: i.agg for i in self.tournament.tournamentinstitution_set.annotate(agg=Count('institution__adjudicator')).all()}

        form = self.get_form()

        table = TabbycatTableBuilder(view=self, title=_('Responses'), sort_key='name')
        table.add_column({'key': 'name', 'title': _("Name")}, [t_inst.institution.name for t_inst in t_institutions])
        table.add_column({'key': 'name', 'title': _("Coach")}, [{
            'text': (coach := t_inst.coach_set.first()).name,
            'link': reverse_tournament('reg-inst-landing', self.tournament, kwargs={'url_key': coach.url_key}),
        } for t_inst in t_institutions])
        if self.tournament.pref('reg_institution_slots'):
            table.add_column({'key': 'teams_requested', 'title': _("Teams Requested")}, [
                {'text': t_inst.teams_requested, 'sort': t_inst.teams_requested} for t_inst in t_institutions
            ])
            table.add_column({'key': 'teams_allocated', 'title': _("Teams Allocated")}, [
                {'text': str(form.get_teams_allocated_field(t_inst.institution)), 'sort': t_inst.teams_allocated} for t_inst in t_institutions
            ])

        if self.tournament.pref('institution_participant_registration'):
            table.add_column({'key': 'teams_registered', 'title': _("Teams Registered")}, [inst_team_count[t_inst.id] for t_inst in t_institutions])

        if self.tournament.pref('reg_institution_slots'):
            table.add_column({'key': 'adjudicators_requested', 'title': _("Adjudicators Requested")}, [
                {'text': t_inst.adjudicators_requested, 'sort': t_inst.adjudicators_requested} for t_inst in t_institutions
            ])
            table.add_column({'key': 'adjudicators_allocated', 'title': _("Adjudicators Allocated")}, [
                {'text': str(form.get_adjs_allocated_field(t_inst.institution)), 'sort': t_inst.adjudicators_allocated} for t_inst in t_institutions
            ])

        if self.tournament.pref('institution_participant_registration'):
            table.add_column({'key': 'adjudicators_registered', 'title': _("Adjudicators Registered")}, [inst_adj_count[t_inst.id] for t_inst in t_institutions])

        handle_question_columns(table, t_institutions)

        return table

    def get_success_url(self):
        return reverse_tournament('reg-institution-list', self.tournament)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tournament'] = self.tournament
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Successfully modified institution allocations"))

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update(self.tournament.tournamentinstitution_set.aggregate(
            adjs_requested=Sum('adjudicators_requested'),
            adjs_allocated=Sum('adjudicators_allocated'),
            teams_requested=Sum('teams_requested'),
            teams_allocated=Sum('teams_allocated'),
        ))
        kwargs['adjs_registered'] = self.tournament.adjudicator_set.filter(institution__isnull=False, adj_core=False, independent=False).count()
        kwargs['teams_registered'] = self.tournament.team_set.filter(institution__isnull=False).count()
        return super().get_context_data(**kwargs)


class TeamRegistrationTableView(TournamentMixin, AdministratorMixin, VueTableTemplateView):
    page_emoji = '👯'
    page_title = gettext_lazy("Team Registration")
    template_name = 'answer_tables/teams.html'

    view_permission = Permission.VIEW_REGISTRATION

    def get_table(self):
        def get_speaker(team, i):
            try:
                return team.speakers[i]
            except IndexError:
                return Speaker()

        teams = self.tournament.team_set.select_related('institution').prefetch_related(
            'answers__question',
            Prefetch('speaker_set', queryset=Speaker.objects.prefetch_related('answers__question')),
        ).all()
        spk_questions = self.tournament.question_set.filter(for_content_type=ContentType.objects.get_for_model(Speaker)).order_by('seq')

        table = TabbycatTableBuilder(view=self, title=_('Responses'), sort_key='team')
        table.add_team_columns(teams)

        handle_question_columns(table, teams)

        for i in range(self.tournament.pref('speakers_in_team')):
            table.add_column({'key': 'spk-%d' % i, 'title': _("Speaker %d") % (i+1,)}, [get_speaker(team, i).name for team in teams])
            table.add_column({'key': 'email-%d' % i, 'title': _("Email")}, [get_speaker(team, i).email for team in teams])

            handle_question_columns(table, [get_speaker(team, i) for team in teams], questions=spk_questions, suffix=i)

        return table


class AdjudicatorRegistrationTableView(TournamentMixin, AdministratorMixin, VueTableTemplateView):
    page_emoji = '👂'
    page_title = gettext_lazy("Adjudicator Registration")
    template_name = 'answer_tables/adjudicators.html'

    view_permission = Permission.VIEW_REGISTRATION

    def get_table(self):
        adjudicators = self.tournament.adjudicator_set.select_related('institution').prefetch_related('answers__question').all()

        table = TabbycatTableBuilder(view=self, title=_('Responses'), sort_key='name')
        table.add_adjudicator_columns(adjudicators, show_metadata=False)
        table.add_column({'key': 'email', 'title': _("Email")}, [adj.email for adj in adjudicators])

        handle_question_columns(table, adjudicators)

        return table


class CustomQuestionFormsetView(TournamentMixin, AdministratorMixin, ModelFormSetView):
    formset_model = Question
    formset_factory_kwargs = {
        'fields': ['name', 'text', 'help_text', 'answer_type', 'required', 'min_value', 'max_value', 'choices'],
        'field_classes': {'choices': SimpleArrayField},
        'extra': 3,
    }
    question_model = None
    template_name = 'questions_edit.html'

    view_permission = True
    edit_permission = Permission.EDIT_QUESTIONS

    page_emoji = '❓'
    page_title = gettext_lazy("Custom Questions")

    def get_page_subtitle(self):
        return _("for %s") % self.question_model._meta.verbose_name_plural

    def get_formset_queryset(self):
        return super().get_formset_queryset().filter(for_content_type=ContentType.objects.get_for_model(self.question_model)).order_by('seq')

    def formset_valid(self, formset):
        self.instances = formset.save(commit=False)
        if self.instances:
            for i, question in enumerate(self.instances, start=1):
                question.tournament = self.tournament
                question.for_content_type = ContentType.objects.get_for_model(self.question_model)
                question.seq = i
                question.save()

            messages.success(self.request, _("Questions for %(model)s were successfully saved.") % {'model': self.question_model._meta.verbose_name_plural})
        else:
            messages.success(self.request, _("No changes were made to the questions."))

        if "add_more" in self.request.POST:
            return HttpResponseRedirect(self.request.path_info)
        return super().formset_valid(formset)

    def get_success_url(self, *args, **kwargs):
        return reverse_tournament(self.success_url, self.tournament)
