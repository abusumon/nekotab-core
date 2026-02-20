"""Core retention engine — schedule, export, and delete tournaments.

This module is intentionally free of Django management-command or Celery
dependencies so it can be called from any entry point.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from tournaments.models import Tournament

from .exporters import export_tournament_csv_zip, export_tournament_json
from .models import TournamentDeletionLog

logger = logging.getLogger(__name__)


def _get_retention_days(override=None):
    if override is not None:
        return override
    return getattr(settings, 'TOURNAMENT_RETENTION_DAYS', 0)


def _get_mode(override=None):
    if override is not None:
        return override
    return getattr(settings, 'TOURNAMENT_RETENTION_MODE', 'EXPORT_THEN_DELETE')


def _get_export_format():
    return getattr(settings, 'TOURNAMENT_EXPORT_FORMAT', 'CSV')


def _get_grace_hours():
    return getattr(settings, 'TOURNAMENT_RETENTION_GRACE_HOURS', 24)


def get_eligible_tournaments(retention_days=None):
    """Return a queryset of tournaments eligible for deletion.

    A tournament is eligible when:
    - ``retention_exempt`` is False
    - ``created_at`` is older than *retention_days* days ago
    - It is not already scheduled (handled separately in the grace flow)
    """
    days = _get_retention_days(retention_days)
    if days <= 0:
        return Tournament.objects.none()

    cutoff = timezone.now() - timedelta(days=days)
    return Tournament.objects.filter(
        retention_exempt=False,
        created_at__lte=cutoff,
        scheduled_for_deletion_at__isnull=True,
    )


def get_scheduled_for_deletion():
    """Return tournaments whose grace period has expired."""
    now = timezone.now()
    return Tournament.objects.filter(
        retention_exempt=False,
        scheduled_for_deletion_at__isnull=False,
        scheduled_for_deletion_at__lte=now,
    )


def _snapshot_counts(tournament):
    """Capture lightweight stats before deletion."""
    from draw.models import Debate
    return {
        'team_count': tournament.team_set.count(),
        'round_count': tournament.round_set.count(),
        'debate_count': Debate.objects.filter(round__tournament=tournament).count(),
    }


def _owner_info(tournament):
    owner = tournament.owner
    if owner:
        return owner.email or '', owner.username
    return '', ''


def _notify_owner(tournament, subject, body):
    """Send an email notification to the tournament owner + configured extras."""
    recipients = list(getattr(settings, 'TOURNAMENT_EXPORT_NOTIFY_EMAILS', []))
    owner_email, _ = _owner_info(tournament)
    if owner_email and owner_email not in recipients:
        recipients.insert(0, owner_email)
    if not recipients:
        return
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=True,
        )
    except Exception:
        logger.exception("Failed to send retention notification for %s", tournament.slug)


def _clear_caches(tournament):
    """Purge all cache keys associated with *tournament*."""
    slug = tournament.slug
    cache.delete(f"{slug}_object")
    cache.delete(f"subdom_tour_exists_{slug}")
    cache.delete(f"subdom_tour_exists_{slug.lower()}")
    # Round caches
    for r in tournament.round_set.values_list('seq', flat=True):
        cache.delete(f"{slug}_{r}_object")


def _export(tournament, fmt=None):
    """Export tournament data and return the archive path."""
    fmt = fmt or _get_export_format()
    if fmt.upper() == 'JSON':
        return export_tournament_json(tournament)
    return export_tournament_csv_zip(tournament)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def schedule_eligible(retention_days=None, dry_run=False):
    """Mark eligible tournaments for deletion (grace period).

    Returns list of (tournament, log) tuples.
    """
    grace_hours = _get_grace_hours()
    deletion_at = timezone.now() + timedelta(hours=grace_hours)
    result = []

    for t in get_eligible_tournaments(retention_days):
        if dry_run:
            log = TournamentDeletionLog.objects.create(
                tournament_id=t.id, slug=t.slug, name=t.name,
                owner_email=_owner_info(t)[0],
                owner_username=_owner_info(t)[1],
                status=TournamentDeletionLog.Status.DRY_RUN,
                **_snapshot_counts(t),
            )
            logger.info("[DRY RUN] Would schedule %s (id=%d) for deletion", t.slug, t.id)
            result.append((t, log))
            continue

        t.scheduled_for_deletion_at = deletion_at
        t.save(update_fields=['scheduled_for_deletion_at'])

        log = TournamentDeletionLog.objects.create(
            tournament_id=t.id, slug=t.slug, name=t.name,
            owner_email=_owner_info(t)[0],
            owner_username=_owner_info(t)[1],
            status=TournamentDeletionLog.Status.SCHEDULED,
            **_snapshot_counts(t),
        )

        _notify_owner(
            t,
            f"[NekoTab] Tournament \"{t.name}\" scheduled for deletion",
            f"Your tournament \"{t.name}\" ({t.slug}) has been idle for "
            f"{_get_retention_days(retention_days)} days and is scheduled for "
            f"archival and deletion in {grace_hours} hours.\n\n"
            f"If you want to keep it, log in and mark it as exempt from "
            f"auto-deletion in the tournament settings.\n\n"
            f"— NekoTab",
        )

        logger.info("Scheduled %s (id=%d) for deletion at %s", t.slug, t.id, deletion_at)
        result.append((t, log))

    return result


def process_deletions(mode=None, dry_run=False):
    """Delete (and optionally export) all tournaments past their grace period.

    Returns list of (slug, log) tuples.
    """
    mode = _get_mode(mode)
    result = []

    for t in get_scheduled_for_deletion():
        owner_email, owner_username = _owner_info(t)
        counts = _snapshot_counts(t)
        archive_path = ''

        if dry_run:
            log = TournamentDeletionLog.objects.create(
                tournament_id=t.id, slug=t.slug, name=t.name,
                owner_email=owner_email, owner_username=owner_username,
                status=TournamentDeletionLog.Status.DRY_RUN,
                **counts,
            )
            logger.info("[DRY RUN] Would delete %s (id=%d)", t.slug, t.id)
            result.append((t.slug, log))
            continue

        try:
            # Export first if required
            if mode == 'EXPORT_THEN_DELETE':
                archive_path = _export(t)
                TournamentDeletionLog.objects.create(
                    tournament_id=t.id, slug=t.slug, name=t.name,
                    owner_email=owner_email, owner_username=owner_username,
                    status=TournamentDeletionLog.Status.EXPORTED,
                    archive_path=archive_path,
                    **counts,
                )

            # Delete in a transaction
            slug = t.slug
            tid = t.id
            name = t.name

            with transaction.atomic():
                _clear_caches(t)
                t.delete()  # CASCADE handles all related objects

            log = TournamentDeletionLog.objects.create(
                tournament_id=tid, slug=slug, name=name,
                owner_email=owner_email, owner_username=owner_username,
                status=TournamentDeletionLog.Status.DELETED,
                archive_path=archive_path,
                **counts,
            )

            _notify_owner(
                type('FakeTournament', (), {'slug': slug, 'owner': None})(),
                f"[NekoTab] Tournament \"{name}\" has been deleted",
                f"Your tournament \"{name}\" ({slug}) has been archived "
                f"and permanently deleted.\n\n"
                + (f"Archive: {archive_path}\n\n" if archive_path else "")
                + f"Teams: {counts['team_count']}, Rounds: {counts['round_count']}, "
                  f"Debates: {counts['debate_count']}\n\n"
                  f"— NekoTab",
            )

            # For post-deletion notification, send to saved email directly
            recipients = list(getattr(settings, 'TOURNAMENT_EXPORT_NOTIFY_EMAILS', []))
            if owner_email and owner_email not in recipients:
                recipients.insert(0, owner_email)
            if recipients:
                try:
                    send_mail(
                        f"[NekoTab] Tournament \"{name}\" has been deleted",
                        f"Your tournament \"{name}\" ({slug}) has been archived "
                        f"and permanently deleted.\n\n"
                        + (f"Archive: {archive_path}\n\n" if archive_path else "")
                        + f"Teams: {counts['team_count']}, "
                          f"Rounds: {counts['round_count']}, "
                          f"Debates: {counts['debate_count']}\n\n"
                          f"— NekoTab",
                        settings.DEFAULT_FROM_EMAIL,
                        recipients,
                        fail_silently=True,
                    )
                except Exception:
                    logger.exception("Failed to send deletion notification for %s", slug)

            logger.info("Deleted tournament %s (id=%d)", slug, tid)
            result.append((slug, log))

        except Exception as exc:
            logger.exception("Failed to process tournament %s (id=%d)", t.slug, t.id)
            TournamentDeletionLog.objects.create(
                tournament_id=t.id, slug=t.slug, name=t.name,
                owner_email=owner_email, owner_username=owner_username,
                status=TournamentDeletionLog.Status.FAILED,
                error_message=str(exc),
                **counts,
            )
            result.append((t.slug, None))

    return result


def run_retention_cycle(retention_days=None, mode=None, dry_run=False):
    """Full retention cycle: schedule eligible → delete past-grace.

    This is the single entry point called by the management command and
    scheduler.
    """
    scheduled = schedule_eligible(retention_days=retention_days, dry_run=dry_run)
    deleted = process_deletions(mode=mode, dry_run=dry_run)
    return scheduled, deleted
