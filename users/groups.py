from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from options.presets import _all_subclasses

from .permissions import Permission


def all_groups():
    yield from _all_subclasses(BaseGroup)


class BaseGroup:
    name: Optional[str] = None
    permissions: List[Permission] = []


class Equity(BaseGroup):
    name = _("Equity")
    permissions = [
        # View and edit all conflicts
        Permission.VIEW_ADJ_TEAM_CONFLICTS,
        Permission.EDIT_ADJ_TEAM_CONFLICTS,
        Permission.VIEW_ADJ_ADJ_CONFLICTS,
        Permission.EDIT_ADJ_ADJ_CONFLICTS,
        Permission.VIEW_ADJ_INST_CONFLICTS,
        Permission.EDIT_ADJ_INST_CONFLICTS,
        Permission.VIEW_TEAM_INST_CONFLICTS,
        Permission.EDIT_TEAM_INST_CONFLICTS,

        # Room constraints
        Permission.VIEW_ROOMCONSTRAINTS,
        Permission.EDIT_ROOMCONSTRAINTS,
        Permission.VIEW_ROOMCATEGORIES,
        Permission.EDIT_ROOMCATEGORIES,

        # Participant identity info
        Permission.VIEW_PARTICIPANTS,
        Permission.VIEW_PARTICIPANT_GENDER,
        Permission.VIEW_PARTICIPANT_CONTACT,
        Permission.VIEW_PARTICIPANT_DECODED,
        Permission.VIEW_PARTICIPANT_INST,
        Permission.VIEW_DECODED_TEAMS,
        Permission.VIEW_ANONYMOUS,

        # Supporting context
        Permission.VIEW_TEAMS,
        Permission.VIEW_ADJUDICATORS,
        Permission.VIEW_ROOMS,
        Permission.VIEW_INSTITUTIONS,
    ]


class AdjudicationCore(BaseGroup):
    # Permissions to make [preformed] allocations, view feedback, and create motions
    name = _("Adjudication Core")
    permissions = [
        Permission.EDIT_FEEDBACK_IGNORE,
        Permission.EDIT_FEEDBACKQUESTION,
        Permission.VIEW_FEEDBACK_UNSUBMITTED,
        Permission.VIEW_FEEDBACK_OVERVIEW,

        # Judging and scoring
        Permission.EDIT_BASEJUDGESCORES_IND,
        Permission.EDIT_ADJ_BREAK,
        Permission.VIEW_ADJ_BREAK,

        # Motions
        Permission.EDIT_MOTION,
        Permission.RELEASE_MOTION,
        Permission.UNRELEASE_MOTION,

        # Adjudicator allocations
        Permission.EDIT_DEBATEADJUDICATORS,
        Permission.EDIT_PREFORMEDPANELS,
        Permission.VIEW_DEBATEADJUDICATORS,

        # Standings and tabs
        Permission.VIEW_BREAK,
        Permission.VIEW_BREAK_OVERVIEW,
        Permission.VIEW_TEAMSTANDINGS,
        Permission.VIEW_SPEAKERSSTANDINGS,
        Permission.VIEW_REPLIESSTANDINGS,
        Permission.VIEW_STANDINGS_OVERVIEW,
        Permission.VIEW_MOTIONSTAB,
        Permission.VIEW_DIVERSITYTAB,

        # Supporting context
        Permission.VIEW_PARTICIPANTS,
        Permission.VIEW_TEAMS,
        Permission.VIEW_ADJUDICATORS,
        Permission.VIEW_ROOMS,
        Permission.VIEW_INSTITUTIONS,
        Permission.VIEW_DECODED_TEAMS,
        Permission.VIEW_ANONYMOUS,
    ]


class TabDirector(BaseGroup):
    # All permissions
    name = _("Tabulation Director")
    permissions = [p for p in Permission]


class TabAssistant(BaseGroup):
    # Permissions to match the Assistant interface
    name = _("Tabulation Assistant")
    permissions = [
        Permission.ADD_BALLOTSUBMISSIONS,
        Permission.MARK_OTHERS_BALLOTSUBMISSIONS,
        Permission.VIEW_BALLOTSUBMISSION_GRAPH,
        Permission.ADD_FEEDBACK,
        Permission.VIEW_INSTITUTIONS,
        Permission.VIEW_PARTICIPANTS,
        Permission.EDIT_PARTICIPANT_CHECKIN,
        Permission.EDIT_ROOM_CHECKIN,
        Permission.VIEW_BRIEFING_DRAW,
        Permission.DISPLAY_MOTION,
    ]


class Language(BaseGroup):
    name = _("Language")
    permissions = [
        Permission.EDIT_BREAK_ELIGIBILITY,
        Permission.EDIT_SPEAKER_CATEGORIES,
        Permission.VIEW_PARTICIPANTS,
        Permission.VIEW_TEAMS,
    ]


class Registration(BaseGroup):
    name = _("Registration")
    permissions = [
        Permission.ADD_TEAMS,
        Permission.VIEW_DECODED_TEAMS,
        Permission.VIEW_ANONYMOUS,
        Permission.ADD_ADJUDICATORS,
        Permission.ADD_INSTITUTIONS,
        Permission.VIEW_PARTICIPANTS,
        Permission.VIEW_PARTICIPANT_GENDER,
        Permission.VIEW_PARTICIPANT_CONTACT,
        Permission.VIEW_PARTICIPANT_DECODED,
        Permission.VIEW_PARTICIPANT_INST,
        Permission.VIEW_SETTINGS,
        Permission.EDIT_QUESTIONS,
        Permission.DELETE_QUESTIONS,
        Permission.VIEW_CUSTOM_ANSWERS,
        Permission.VIEW_REGISTRATION,
    ]


def tab_director_group_names():
    """The Tabulation Director group's name in every site language (the name is
    stored translated, in whatever language the tournament was created in)."""
    from django.conf import settings
    from django.utils import translation
    names = {"Tabulation Director"}
    for code, _name in settings.LANGUAGES:
        with translation.override(code):
            names.add(str(TabDirector.name))
    return names


def ensure_role_groups(tournament):
    """Create any missing standard roles and top up existing ones with
    permissions added since they were created. Never removes a permission a
    director granted by hand."""
    from .models import Group
    existing = {g.name: g for g in Group.objects.filter(tournament=tournament)}
    for preset in all_groups():
        name = str(preset.name)
        group = existing.get(name)
        if group is None:
            Group.objects.create(name=name, permissions=list(preset.permissions), tournament=tournament)
            continue
        missing = [p for p in preset.permissions if p not in (group.permissions or [])]
        if missing:
            group.permissions = list(group.permissions or []) + missing
            group.save(update_fields=['permissions'])


ROLE_SUMMARIES = {
    'TabDirector': _("Full access, the same as the owner: setup, draws, results, the break, "
                     "settings, and inviting or removing people."),
    'TabAssistant': _("Assistant pages only: enter ballots and feedback, check people in, "
                      "show draws and motions. Cannot change setup or results."),
    'AdjudicationCore': _("Allocate adjudicators and panels, read feedback, write and release "
                          "motions, see standings and the break."),
    'Equity': _("View and edit conflicts and room constraints, and see participants' "
                "identity details."),
    'Language': _("Set speaker categories (e.g. ESL/EFL) and break eligibility."),
    'Registration': _("Add teams, adjudicators and institutions, and read registration answers."),
}


def describe_role(group):
    """(summary, preset class name) for a tournament's role group."""
    for preset in all_groups():
        if str(preset.name) == group.name:
            return ROLE_SUMMARIES.get(preset.__name__, ''), preset.__name__
    return _("Custom role."), ''
