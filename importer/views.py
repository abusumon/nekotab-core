import logging
from xml.etree import ElementTree

from defusedxml.ElementTree import fromstring
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import management
from django.forms import modelformset_factory
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, ngettext
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from formtools.wizard.views import SessionWizardView

from actionlog.mixins import LogActionMixin
from actionlog.models import ActionLogEntry
from participants.emoji import set_emoji
from participants.models import Adjudicator, Institution, Person, Team
from participants.utils import populate_code_names
from tournaments.mixins import TournamentMixin
from tournaments.models import Tournament
from users.permissions import Permission
from utils.misc import redirect_tournament, reverse_tournament
from utils.mixins import AdministratorMixin
from utils.views import PostOnlyRedirectView
from venues.models import Venue

from .archive import Exporter, Importer
from .forms import (AdjudicatorDetailsForm, ArchiveImportForm, ImportAdjudicatorsNumbersForm,
                    ImportInstitutionsRawForm, ImportTeamsNumbersForm,
                    ImportVenuesRawForm, TeamDetailsForm, TeamDetailsFormSet,
                    VenueDetailsForm)
from .importers import TournamentDataImporterError
from .management.commands import importtournament

logger = logging.getLogger(__name__)


class ImporterSimpleIndexView(AdministratorMixin, TournamentMixin, TemplateView):
    template_name = 'simple_import_index.html'
    view_permission = True


class BaseImportWizardView(AdministratorMixin, LogActionMixin, TournamentMixin, SessionWizardView):
    """Common functionality for the import wizard views. In particular, this
    class implements functionality for a "details" step that is initialized
    with data from the previous step. The details step shows a ModelFormSet
    associated with a specified model."""

    DETAILS_STEP = 'details'
    tournament_redirect_pattern_name = 'importer-simple-index'

    model = None  # must be specified by subclass

    def get_details_form_initial(self):
        raise NotImplementedError

    def get_template_names(self):
        return ['simple_import_%(model)ss_%(step)s.html' % {
            'model': self.model._meta.model_name,
            'step': self.steps.current,
        }]

    def get_form_initial(self, step):
        """Overridden to initialize the 'details' step with data from a previous
        step."""
        if step == self.DETAILS_STEP and step == self.steps.next:
            return self.get_details_form_initial()
        else:
            return super().get_form_initial(step)

    def get_form_instance(self, step):
        if step == self.DETAILS_STEP:
            return self.model.objects.none()
        else:
            return super().get_form_instance(step)

    def get_form(self, step=None, **kwargs):
        form = super().get_form(step, **kwargs)
        if step == self.DETAILS_STEP:
            form.extra = len(form.initial_extra)
            form.save_as_new = True
        return form

    def get_message(self, count):
        raise NotImplementedError

    def done(self, form_list, form_dict, **kwargs):
        self.instances = form_dict[self.DETAILS_STEP].save()
        count = len(self.instances)
        messages.success(self.request, self.get_message(count) % {'count': count})
        self.log_action()
        return HttpResponseRedirect(self.get_redirect_url())


class ImportInstitutionsWizardView(BaseImportWizardView):
    model = Institution
    edit_permission = Permission.ADD_INSTITUTIONS
    form_list = [
        ('raw', ImportInstitutionsRawForm),
        ('details', modelformset_factory(Institution, fields=('name', 'code'), extra=0)),
    ]
    action_log_type = ActionLogEntry.ActionType.SIMPLE_IMPORT_INSTITUTIONS

    def get_details_form_initial(self):
        return self.get_cleaned_data_for_step('raw')['institutions_raw']

    def get_message(self, count):
        return ngettext("Added %(count)d institution.", "Added %(count)d institutions.", count)


class ImportVenuesWizardView(BaseImportWizardView):
    model = Venue
    edit_permission = Permission.ADD_ROOMS
    form_list = [
        ('raw', ImportVenuesRawForm),
        ('details', modelformset_factory(Venue, form=VenueDetailsForm, extra=0)),
    ]
    action_log_type = ActionLogEntry.ActionType.SIMPLE_IMPORT_VENUES

    def get_form_kwargs(self, step):
        if step == 'details':
            return {'form_kwargs': {'tournament': self.tournament}}
        else:
            return super().get_form_kwargs(step)

    def get_details_form_initial(self):
        return self.get_cleaned_data_for_step('raw')['venues_raw']

    def get_message(self, count):
        return ngettext("Added %(count)d room.", "Added %(count)d rooms.", count)


class BaseImportByInstitutionWizardView(BaseImportWizardView):
    """Common functionality in teams and institutions wizards."""

    def get_form_kwargs(self, step):
        if step == 'numbers':
            return {
                'institutions': Institution.objects.all(),
            }
        elif step == 'details':
            return {'form_kwargs': {'tournament': self.tournament}}

    def make_initial_data(self, number, institution_id):
        if number is None:  # occurs when field was left blank
            return []
        initial_list = []
        for i in range(1, number+1):
            initial = {'institution': institution_id}
            initial.update(self.get_details_instance_initial(i))
            initial_list.append(initial)
        return initial_list

    def get_details_form_initial(self):
        data = self.get_cleaned_data_for_step('numbers')
        initial_list = []

        nunaffiliated = data.get('number_unaffiliated')
        initial_list.extend(self.make_initial_data(nunaffiliated, None))

        for institution in Institution.objects.order_by('name'):
            number = data.get('number_institution_%d' % institution.id)
            initial_list.extend(self.make_initial_data(number, institution.id))

        return initial_list

    def get_details_instance_initial(self):
        raise NotImplementedError


class ImportTeamsWizardView(BaseImportByInstitutionWizardView):
    model = Team
    edit_permission = Permission.ADD_TEAMS
    form_list = [
        ('numbers', ImportTeamsNumbersForm),
        ('details', modelformset_factory(Team, form=TeamDetailsForm, formset=TeamDetailsFormSet, extra=0)),
    ]
    action_log_type = ActionLogEntry.ActionType.SIMPLE_IMPORT_TEAMS

    def get_details_instance_initial(self, i):
        return {'reference': str(i), 'use_institution_prefix': True}

    def done(self, form_list, form_dict, **kwargs):
        # Also set emoji on teams and code names on speakers
        redirect = super().done(form_list, form_dict, **kwargs)
        set_emoji(self.instances, self.tournament)
        populate_code_names(Person.objects.filter(speaker__team__in=self.instances))
        return redirect

    def get_message(self, count):
        return ngettext("Added %(count)d team.", "Added %(count)d teams.", count)


class ImportAdjudicatorsWizardView(BaseImportByInstitutionWizardView):
    model = Adjudicator
    edit_permission = Permission.ADD_ADJUDICATORS
    form_list = [
        ('numbers', ImportAdjudicatorsNumbersForm),
        ('details', modelformset_factory(Adjudicator, form=AdjudicatorDetailsForm, extra=0)),
    ]
    action_log_type = ActionLogEntry.ActionType.SIMPLE_IMPORT_ADJUDICATORS

    def get_default_base_score(self):
        """Returns the midpoint of the configured allowable score range."""
        if not hasattr(self, "_default_base_score"):
            min_score = self.tournament.pref('adj_min_score')
            max_score = self.tournament.pref('adj_max_score')
            self._default_base_score = (min_score + max_score) / 2
        return self._default_base_score

    def get_details_instance_initial(self, i):
        return {
            'name': _("Adjudicator %(number)d") % {'number': i},
            'base_score': self.get_default_base_score(),
        }

    def done(self, form_list, form_dict, **kwargs):
        # Also set code names on adjudicators
        redirect = super().done(form_list, form_dict, **kwargs)
        populate_code_names(self.instances)
        return redirect

    def get_message(self, count):
        return ngettext("Added %(count)d adjudicator.", "Added %(count)d adjudicators.", count)


class LoadDemoView(AdministratorMixin, PostOnlyRedirectView):

    def post(self, request, *args, **kwargs):
        source = request.POST.get("source", "")

        if source not in ['minimal8team', 'australs24team', 'bp88team']:
            return HttpResponseBadRequest("%s isn't a demo dataset" % source)

        try:
            management.call_command(importtournament.Command(), source,
                                    force=True, strict=False, encoding='utf-8')
        except TournamentDataImporterError as e:
            messages.error(self.request, mark_safe(_(
                "<p>There were one or more errors creating the demo tournament. "
                "Before retrying, please delete the existing demo tournament "
                "<strong>and</strong> the institutions in the Edit Database Area.</p>"
                "<p><i>Technical information: The errors are as follows:</i></p>",
            ) + "<ul><li><i>" + "</i></li><li><i>".join(e.itermessages()) + "</i></li></ul>"))
            logger.error("Error importing demo tournament: " + str(e))
            return redirect('tabbycat-index')
        else:
            messages.success(self.request, _("Created new demo tournament. You "
                "can now configure it below."))

        new_tournament = Tournament.objects.get(slug=source)
        return redirect_tournament('tournament-configure', tournament=new_tournament)


class TournamentImportArchiveView(AdministratorMixin, FormView):

    form_class = ArchiveImportForm
    success_url = reverse_lazy('tabbycat-index')
    template_name = 'archive_importer.html'
    view_role = ""

    def form_valid(self, form):
        self.importer = Importer(fromstring(form.cleaned_data['xml']))
        self.importer.import_tournament()

        messages.success(self.request, _("Tournament archive has been imported."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_tournament('tournament-admin-home', self.importer.tournament)


class ExportArchiveIndexView(AdministratorMixin, TournamentMixin, TemplateView):

    template_name = 'archive_export_index.html'
    view_permission = Permission.EXPORT_XML


class ExportArchiveAllView(AdministratorMixin, TournamentMixin, View):
    view_permission = Permission.EXPORT_XML

    def get(self, request, *args, **kwargs):
        response = HttpResponse(self.get_xml(), content_type='text/xml; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="' + self.tournament.short_name + '.xml"'

        return response

    def get_xml(self):
        return ElementTree.tostring(Exporter(self.tournament).create_all())



class HomeImportCalICOTabView(LoginRequiredMixin, View):
    """XML file upload from the homepage CalICOTab import box.
    Supports optional slug override and pre-checks for slug conflicts."""

    def get(self, request, *args, **kwargs):
        return render(request, 'calicotab_import.html')

    def post(self, request, *args, **kwargs):
        from django.template.defaultfilters import slugify as django_slugify
        xml_file = request.FILES.get('xml_file')
        slug_override = request.POST.get('slug_override', '').strip()

        if not xml_file:
            messages.error(request, _("No file uploaded. Please select an XML file."))
            return redirect('tabbycat-index')
        if not xml_file.name.endswith('.xml'):
            messages.error(request, _("Invalid file type. Please upload a .xml file."))
            return redirect('tabbycat-index')

        try:
            xml_bytes = xml_file.read()
            root = fromstring(xml_bytes)
        except Exception as e:
            messages.error(request, _("Could not parse XML file: %s") % str(e))
            return redirect('tabbycat-index')

        # Determine intended slug
        tournament_name = root.get('name', 'imported-tournament')
        if slug_override:
            intended_slug = django_slugify(slug_override)
            if not intended_slug:
                messages.error(request, _("Invalid slug. Use letters, numbers and hyphens only."))
                return redirect('tabbycat-index')
        else:
            intended_slug = django_slugify(tournament_name)

        # Pre-check slug conflict
        if Tournament.objects.filter(slug=intended_slug).exists():
            messages.error(request, _(
                "A tournament with slug \"%(slug)s\" already exists. "
                "Please choose a different slug in the import form."
            ) % {'slug': intended_slug})
            return redirect('tabbycat-index')

        try:
            importer = Importer(root)
            importer.import_tournament()
        except Exception as e:
            messages.error(request, _("Import failed: %s") % str(e))
            logger.exception("CalICOTab XML import error")
            return redirect('tabbycat-index')

        # Apply slug override after creation
        if slug_override and importer.tournament.slug != intended_slug:
            importer.tournament.slug = intended_slug
            importer.tournament.save(update_fields=['slug'])

        messages.success(request, _("Tournament imported successfully! Welcome to NekoTab."))
        return redirect_tournament('tournament-admin-home', importer.tournament)


class ImportToolView(TemplateView):
    """Public CSV importer tool — wraps the CSV-Importers frontend with a
    NekoTab UI. No tournament context required; communicates with the API directly."""
    template_name = 'import_tool.html'

    CSV_TYPES = [
        ('Institutions', '🏫', 'institutions.csv'),
        ('Teams', '👥', 'teams.csv'),
        ('Speakers', '🎤', 'speakers.csv'),
        ('Adjudicators', '⚖️', 'adjudicators.csv'),
        ('Venues', '🏛️', 'venues.csv'),
        ('Rounds', '🔄', 'rounds.csv'),
        ('Motions', '📋', 'motions.csv'),
        ('Break Categories', '🏆', 'break_categories.csv'),
        ('Venue Categories', '📍', 'venue_categories.csv'),
        ('Adj Scores', '🎯', 'scores.csv'),
        ('Speaker Categories', '🏷️', 'speaker_categories.csv'),
        ('Adj Conflicts', '⚔️', 'adjudicator_conflicts.csv'),
        ('Team Conflicts', '⚡', 'team_conflicts.csv'),
        ('Adj Venue Constraints', '📐', 'adj_venue_constraints.csv'),
        ('Team Venue Constraints', '📐', 'team_venue_constraints.csv'),
        ('Feedback Questions', '💬', 'adj_feedback_questions.csv'),
    ]

    CALICO_FEATURES = [
        'Teams & speakers', 'Adjudicators & panels',
        'Venues & rounds', 'Ballots & scores',
        'Motions', 'Draw structure',
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['csv_types'] = self.CSV_TYPES
        ctx['calico_features'] = self.CALICO_FEATURES
        return ctx
