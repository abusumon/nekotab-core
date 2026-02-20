"""Management command to run the tournament retention/cleanup cycle.

Usage examples:

    # Dry run — show what would happen
    python manage.py purge_tournaments --dry-run

    # Use settings defaults
    python manage.py purge_tournaments

    # Override retention window and mode
    python manage.py purge_tournaments --retention-days 14 --mode export-delete

    # Delete-only (no export)
    python manage.py purge_tournaments --mode delete
"""

import logging

from django.core.management.base import BaseCommand

from retention.engine import (
    get_eligible_tournaments,
    get_scheduled_for_deletion,
    run_retention_cycle,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Run the tournament retention cycle: schedule eligible tournaments "
        "for deletion, then process (export + delete) tournaments past their "
        "grace period."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would happen without making changes.',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=None,
            help='Override TOURNAMENT_RETENTION_DAYS setting.',
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['delete', 'export-delete'],
            default=None,
            help='Override TOURNAMENT_RETENTION_MODE. '
                 '"delete" = DELETE_ONLY, "export-delete" = EXPORT_THEN_DELETE.',
        )
        parser.add_argument(
            '--export-dir',
            type=str,
            default=None,
            help='Directory to write archive zip files into (overrides MEDIA_ROOT/archives/).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        retention_days = options['retention_days']
        mode_arg = options['mode']
        export_dir = options['export_dir']

        # Map CLI arg to settings constant
        mode_map = {
            'delete': 'DELETE_ONLY',
            'export-delete': 'EXPORT_THEN_DELETE',
            None: None,
        }
        mode = mode_map.get(mode_arg)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN ==='))
            self.stdout.write('')

            eligible = get_eligible_tournaments(retention_days)
            self.stdout.write(f'Tournaments eligible for scheduling: {eligible.count()}')
            for t in eligible:
                self.stdout.write(f'  • {t.slug} (id={t.id}, created={t.created_at})')

            past_grace = get_scheduled_for_deletion()
            self.stdout.write(f'\nTournaments past grace period: {past_grace.count()}')
            for t in past_grace:
                self.stdout.write(
                    f'  • {t.slug} (id={t.id}, scheduled_at={t.scheduled_for_deletion_at})'
                )
            self.stdout.write('')

        scheduled, deleted = run_retention_cycle(
            retention_days=retention_days,
            mode=mode,
            dry_run=dry_run,
            export_dir=export_dir,
        )

        # Report
        self.stdout.write('')
        if scheduled:
            self.stdout.write(self.style.SUCCESS(f'Scheduled: {len(scheduled)} tournament(s)'))
            for t, log in scheduled:
                status = log.status if log else '?'
                self.stdout.write(f'  [{status}] {t.slug if hasattr(t, "slug") else t}')
        else:
            self.stdout.write('No tournaments to schedule.')

        if deleted:
            self.stdout.write(self.style.SUCCESS(f'Processed: {len(deleted)} tournament(s)'))
            for slug, log in deleted:
                status = log.status if log else 'FAILED'
                self.stdout.write(f'  [{status}] {slug}')
        else:
            self.stdout.write('No tournaments to delete.')

        self.stdout.write(self.style.SUCCESS('\nDone.'))
