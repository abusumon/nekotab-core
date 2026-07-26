"""Delete demo tournaments whose lifetime has run out.

Run by Celery Beat (``tournaments.tasks.cleanup_expired_demos``); this command
is the manual and debugging entry point, matching how ``purge_tournaments``
fronts the retention engine.

    python manage.py cleanup_expired_demos --dry-run
    python manage.py cleanup_expired_demos

Deletion goes through the same PROTECT-clearing and cache-purging steps the
retention engine uses. A bare ``tournament.delete()`` raises ``ProtectedError``:
several models reference a tournament's rounds with ``on_delete=PROTECT``, and
Django raises even when the protecting rows are themselves part of the same
cascade.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tournaments.models import Tournament

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete demo tournaments whose expires_at has passed."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='List what would be deleted without deleting anything.')
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Delete at most this many (0 = no limit). Useful if a backlog '
                 'has built up and you would rather drain it in batches.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        expired = Tournament.objects.expired_demos().order_by('expires_at')
        if limit:
            expired = expired[:limit]

        # Materialise before deleting — the queryset is re-evaluated otherwise
        # and rows shift underneath the loop.
        targets = list(expired)

        if not targets:
            self.stdout.write("No expired demo tournaments.")
            return 0

        deleted, failed = 0, 0
        for tournament in targets:
            label = f'{tournament.slug} (#{tournament.pk}, expired {tournament.expires_at})'
            if dry_run:
                self.stdout.write(f'  would delete {label}')
                continue
            if self._delete(tournament, label):
                deleted += 1
            else:
                failed += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Dry run: {len(targets)} demo tournament(s) would be deleted.'))
            return 0

        style = self.style.SUCCESS if not failed else self.style.WARNING
        self.stdout.write(style(
            f'Deleted {deleted} expired demo tournament(s); {failed} failed.'))
        return 0

    def _delete(self, tournament, label):
        """Delete one demo. Returns True on success.

        Failures are logged and swallowed so that one undeletable tournament
        cannot stop the rest of the batch — a scheduled cleanup that aborts
        halfway silently stops reclaiming anything.
        """
        from retention.engine import _clear_caches, _clear_protect_refs

        try:
            with transaction.atomic():
                _clear_protect_refs(tournament)
                _clear_caches(tournament)
                tournament.delete()
        except Exception:
            logger.exception('Could not delete expired demo tournament %s', label)
            self.stdout.write(self.style.ERROR(f'  FAILED {label}'))
            return False

        logger.info('Deleted expired demo tournament %s', label)
        self.stdout.write(f'  deleted {label}')
        return True
