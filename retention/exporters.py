"""Tournament data exporter — multi-CSV zip or single JSON archive.

All export helpers in this module are **streaming-friendly**: they iterate over
Django querysets in chunks rather than loading all rows into memory at once.
"""

import csv
import io
import json
import logging
import os
import zipfile
from datetime import datetime

from django.conf import settings
from django.db.models import Prefetch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV table specifications
#
# Each entry maps a filename (inside the zip) to:
#   queryset_fn  — callable(tournament) → QuerySet
#   columns      — list of column names (supports ``__`` lookups and callables)
# ---------------------------------------------------------------------------

def _qs_tournament(t):
    """Return a single-row 'queryset' for the tournament itself."""
    from tournaments.models import Tournament
    return Tournament.objects.filter(pk=t.pk)


def _qs_rounds(t):
    from tournaments.models import Round
    return Round.objects.filter(tournament=t).order_by('seq')


def _qs_teams(t):
    from participants.models import Team
    return (Team.objects.filter(tournament=t)
            .select_related('institution')
            .order_by('id'))


def _qs_speakers(t):
    from participants.models import Speaker
    return (Speaker.objects.filter(team__tournament=t)
            .select_related('team', 'team__institution')
            .order_by('id'))


def _qs_adjudicators(t):
    from participants.models import Adjudicator
    return (Adjudicator.objects.filter(tournament=t)
            .select_related('institution')
            .order_by('id'))


def _qs_institutions(t):
    from participants.models import TournamentInstitution
    return (TournamentInstitution.objects.filter(tournament=t)
            .select_related('institution', 'institution__region')
            .order_by('id'))


def _qs_debates(t):
    from draw.models import Debate
    return (Debate.objects.filter(round__tournament=t)
            .select_related('round', 'venue')
            .order_by('round__seq', 'id'))


def _qs_debate_teams(t):
    from draw.models import DebateTeam
    return (DebateTeam.objects.filter(debate__round__tournament=t)
            .select_related('debate', 'debate__round', 'team')
            .order_by('debate__round__seq', 'debate__id', 'side'))


def _qs_debate_adjudicators(t):
    from adjallocation.models import DebateAdjudicator
    return (DebateAdjudicator.objects.filter(debate__round__tournament=t)
            .select_related('debate', 'debate__round', 'adjudicator')
            .order_by('debate__round__seq', 'debate__id'))


def _qs_ballots(t):
    from results.models import BallotSubmission
    return (BallotSubmission.objects.filter(debate__round__tournament=t)
            .select_related('debate', 'debate__round', 'motion')
            .order_by('debate__round__seq', 'debate__id', 'version'))


def _qs_team_scores(t):
    from results.models import TeamScore
    return (TeamScore.objects.filter(
                ballot_submission__debate__round__tournament=t,
                ballot_submission__confirmed=True)
            .select_related('ballot_submission', 'debate_team', 'debate_team__team')
            .order_by('ballot_submission__debate__round__seq', 'id'))


def _qs_speaker_scores(t):
    from results.models import SpeakerScore
    return (SpeakerScore.objects.filter(
                ballot_submission__debate__round__tournament=t,
                ballot_submission__confirmed=True)
            .select_related('ballot_submission', 'debate_team', 'speaker')
            .order_by('ballot_submission__debate__round__seq', 'id'))


def _qs_motions(t):
    from motions.models import Motion
    return Motion.objects.filter(tournament=t).order_by('id')


def _qs_round_motions(t):
    from motions.models import RoundMotion
    return (RoundMotion.objects.filter(round__tournament=t)
            .select_related('round', 'motion')
            .order_by('round__seq', 'seq'))


def _qs_feedback(t):
    from adjfeedback.models import AdjudicatorFeedback
    return (AdjudicatorFeedback.objects.filter(
                adjudicator__tournament=t)
            .select_related('adjudicator', 'source_adjudicator',
                            'source_team')
            .order_by('id'))


def _qs_break_categories(t):
    from breakqual.models import BreakCategory
    return BreakCategory.objects.filter(tournament=t).order_by('seq')


def _qs_breaking_teams(t):
    from breakqual.models import BreakingTeam
    return (BreakingTeam.objects.filter(break_category__tournament=t)
            .select_related('break_category', 'team')
            .order_by('break_category__seq', 'rank'))


def _qs_venues(t):
    from venues.models import Venue
    return Venue.objects.filter(tournament=t).order_by('id')


def _qs_user_permissions(t):
    from users.models import UserPermission
    return (UserPermission.objects.filter(tournament=t)
            .select_related('user')
            .order_by('id'))


def _qs_groups(t):
    from users.models import Group
    return Group.objects.filter(tournament=t).order_by('id')


def _qs_schedule_events(t):
    from tournaments.models import ScheduleEvent
    return (ScheduleEvent.objects.filter(tournament=t)
            .order_by('start_time'))


def _qs_adj_conflicts_team(t):
    from adjallocation.models import AdjudicatorTeamConflict
    return (AdjudicatorTeamConflict.objects.filter(adjudicator__tournament=t)
            .select_related('adjudicator', 'team')
            .order_by('id'))


def _qs_adj_conflicts_adj(t):
    from adjallocation.models import AdjudicatorAdjudicatorConflict
    return (AdjudicatorAdjudicatorConflict.objects.filter(adjudicator1__tournament=t)
            .select_related('adjudicator1', 'adjudicator2')
            .order_by('id'))


def _qs_adj_conflicts_inst(t):
    from adjallocation.models import AdjudicatorInstitutionConflict
    return (AdjudicatorInstitutionConflict.objects.filter(adjudicator__tournament=t)
            .select_related('adjudicator', 'institution')
            .order_by('id'))


# ---------------------------------------------------------------------------
# Column extractors — safe attribute access with ``__`` traversal
# ---------------------------------------------------------------------------

def _get_value(obj, col):
    """Resolve a dotted/dunder column spec on *obj*, e.g. ``team__short_name``."""
    parts = col.split('__')
    val = obj
    for p in parts:
        if val is None:
            return ''
        val = getattr(val, p, '')
    return val if val is not None else ''


# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------

CSV_TABLES = [
    ('tournament.csv', _qs_tournament, [
        'id', 'name', 'short_name', 'slug', 'active', 'created_at',
    ]),
    ('rounds.csv', _qs_rounds, [
        'id', 'seq', 'name', 'abbreviation', 'stage', 'draw_type',
        'draw_status', 'completed', 'silent', 'motions_released',
        'feedback_weight', 'starts_at', 'weight',
    ]),
    ('institutions.csv', _qs_institutions, [
        'id', 'institution__name', 'institution__code',
        'institution__region__name',
        'teams_requested', 'teams_allocated',
        'adjudicators_requested', 'adjudicators_allocated',
    ]),
    ('teams.csv', _qs_teams, [
        'id', 'reference', 'short_reference', 'short_name', 'long_name',
        'code_name', 'institution__name', 'use_institution_prefix',
        'emoji', 'seed', 'type',
    ]),
    ('speakers.csv', _qs_speakers, [
        'id', 'name', 'email', 'gender', 'team__short_name', 'team__id',
        'anonymous', 'code_name',
    ]),
    ('adjudicators.csv', _qs_adjudicators, [
        'id', 'name', 'email', 'gender', 'institution__name',
        'base_score', 'trainee', 'breaking', 'independent', 'adj_core',
    ]),
    ('venues.csv', _qs_venues, [
        'id', 'name', 'priority',
    ]),
    ('debates.csv', _qs_debates, [
        'id', 'round__seq', 'round__name', 'venue__name',
        'bracket', 'room_rank', 'importance', 'result_status',
        'sides_confirmed',
    ]),
    ('debate_teams.csv', _qs_debate_teams, [
        'id', 'debate__id', 'debate__round__seq', 'team__short_name',
        'team__id', 'side',
    ]),
    ('debate_adjudicators.csv', _qs_debate_adjudicators, [
        'id', 'debate__id', 'debate__round__seq',
        'adjudicator__name', 'adjudicator__id', 'type',
    ]),
    ('motions.csv', _qs_motions, [
        'id', 'reference', 'text', 'info_slide',
    ]),
    ('round_motions.csv', _qs_round_motions, [
        'id', 'round__seq', 'round__name', 'motion__reference',
        'motion__id', 'seq',
    ]),
    ('ballots.csv', _qs_ballots, [
        'id', 'debate__id', 'debate__round__seq', 'version',
        'confirmed', 'discarded', 'timestamp', 'submitter_type',
        'motion__reference', 'forfeit', 'single_adj',
    ]),
    ('team_scores.csv', _qs_team_scores, [
        'id', 'ballot_submission__id', 'debate_team__team__short_name',
        'debate_team__team__id', 'points', 'win', 'margin', 'score',
        'votes_given', 'votes_possible',
    ]),
    ('speaker_scores.csv', _qs_speaker_scores, [
        'id', 'ballot_submission__id', 'speaker__name', 'speaker__id',
        'debate_team__team__short_name', 'score', 'position', 'ghost',
        'rank',
    ]),
    ('feedback.csv', _qs_feedback, [
        'id', 'adjudicator__name', 'adjudicator__id', 'score',
        'confirmed', 'ignored', 'timestamp', 'version',
    ]),
    ('break_categories.csv', _qs_break_categories, [
        'id', 'name', 'slug', 'seq', 'break_size', 'is_general',
        'priority', 'rule',
    ]),
    ('breaking_teams.csv', _qs_breaking_teams, [
        'id', 'break_category__name', 'team__short_name', 'team__id',
        'rank', 'break_rank', 'remark',
    ]),
    ('user_permissions.csv', _qs_user_permissions, [
        'id', 'user__username', 'user__email', 'permission',
    ]),
    ('groups.csv', _qs_groups, [
        'id', 'name', 'permissions',
    ]),
    ('schedule_events.csv', _qs_schedule_events, [
        'id', 'title', 'type', 'start_time', 'end_time', 'round__seq',
    ]),
    ('adj_team_conflicts.csv', _qs_adj_conflicts_team, [
        'id', 'adjudicator__name', 'adjudicator__id', 'team__short_name', 'team__id',
    ]),
    ('adj_adj_conflicts.csv', _qs_adj_conflicts_adj, [
        'id', 'adjudicator1__name', 'adjudicator1__id',
        'adjudicator2__name', 'adjudicator2__id',
    ]),
    ('adj_institution_conflicts.csv', _qs_adj_conflicts_inst, [
        'id', 'adjudicator__name', 'adjudicator__id',
        'institution__name', 'institution__id',
    ]),
]

CHUNK_SIZE = 2000


def export_tournament_csv_zip(tournament, output_path=None):
    """Export *tournament* as a multi-CSV zip file.

    Args:
        tournament: A ``Tournament`` model instance.
        output_path: Optional absolute path for the zip.  If ``None``, the
            archive is written to ``MEDIA_ROOT/archives/<slug>-<id>-archive.zip``.

    Returns:
        The absolute path to the created zip file.
    """
    if output_path is None:
        archive_dir = os.path.join(settings.MEDIA_ROOT, 'archives')
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f'{tournament.slug}-{tournament.id}-{ts}-archive.zip'
        output_path = os.path.join(archive_dir, filename)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for csv_name, qs_fn, columns in CSV_TABLES:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(columns)

            qs = qs_fn(tournament)
            for batch_start in range(0, qs.count(), CHUNK_SIZE):
                for obj in qs[batch_start:batch_start + CHUNK_SIZE]:
                    writer.writerow([_get_value(obj, c) for c in columns])

            zf.writestr(csv_name, buf.getvalue())

        # Include a manifest
        manifest = {
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'tournament_slug': tournament.slug,
            'exported_at': datetime.utcnow().isoformat(),
            'format': 'multi-csv-zip',
            'tables': [t[0] for t in CSV_TABLES],
        }
        zf.writestr('_manifest.json', json.dumps(manifest, indent=2))

    logger.info("Exported tournament %s (id=%d) to %s", tournament.slug, tournament.id, output_path)
    return output_path


def export_tournament_json(tournament, output_path=None):
    """Export *tournament* as a single structured JSON file.

    Returns:
        The absolute path to the created JSON file.
    """
    if output_path is None:
        archive_dir = os.path.join(settings.MEDIA_ROOT, 'archives')
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f'{tournament.slug}-{tournament.id}-{ts}-archive.json'
        output_path = os.path.join(archive_dir, filename)

    data = {
        '_meta': {
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'tournament_slug': tournament.slug,
            'exported_at': datetime.utcnow().isoformat(),
            'format': 'json',
        },
    }

    for csv_name, qs_fn, columns in CSV_TABLES:
        table_key = csv_name.replace('.csv', '')
        rows = []
        qs = qs_fn(tournament)
        for batch_start in range(0, qs.count(), CHUNK_SIZE):
            for obj in qs[batch_start:batch_start + CHUNK_SIZE]:
                rows.append({c: str(_get_value(obj, c)) for c in columns})
        data[table_key] = rows

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info("Exported tournament %s (id=%d) to %s", tournament.slug, tournament.id, output_path)
    return output_path
