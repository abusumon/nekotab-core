"""Tests for the retention app — engine, exporters, and management command.

Covers:
  - Tournament eligibility detection
  - Grace period scheduling
  - Multi-CSV zip export (file creation and content)
  - Audit log creation
  - Dry-run mode (no side-effects)
  - ``retention_exempt`` flag
  - Management command output
"""

import os
import tempfile
import zipfile
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from retention.engine import (
    get_eligible_tournaments,
    get_scheduled_for_deletion,
    run_retention_cycle,
    schedule_eligible,
)
from retention.exporters import export_tournament_csv_zip
from retention.models import TournamentDeletionLog
from tournaments.models import Tournament


class EligibilityTestCase(TestCase):
    """Tests for ``get_eligible_tournaments``."""

    def setUp(self):
        self.old_t = Tournament.objects.create(
            slug='old', name='Old', active=True,
        )
        # Backdating: Django auto_now_add prevents direct assignment so we
        # use queryset.update() to bypass.
        Tournament.objects.filter(pk=self.old_t.pk).update(
            created_at=timezone.now() - timedelta(days=120),
        )
        self.old_t.refresh_from_db()

        self.new_t = Tournament.objects.create(
            slug='new', name='New', active=True,
        )
        self.exempt_t = Tournament.objects.create(
            slug='exempt', name='Exempt', active=True,
            retention_exempt=True,
        )
        Tournament.objects.filter(pk=self.exempt_t.pk).update(
            created_at=timezone.now() - timedelta(days=120),
        )
        self.exempt_t.refresh_from_db()

    def tearDown(self):
        Tournament.objects.all().delete()

    def test_old_tournament_is_eligible(self):
        eligible = get_eligible_tournaments(retention_days=90)
        self.assertIn(self.old_t, eligible)

    def test_new_tournament_not_eligible(self):
        eligible = get_eligible_tournaments(retention_days=90)
        self.assertNotIn(self.new_t, eligible)

    def test_exempt_tournament_not_eligible(self):
        eligible = get_eligible_tournaments(retention_days=90)
        self.assertNotIn(self.exempt_t, eligible)

    def test_zero_retention_returns_none(self):
        eligible = get_eligible_tournaments(retention_days=0)
        self.assertEqual(len(eligible), 0)


class ScheduleTestCase(TestCase):
    """Tests for ``schedule_eligible`` and ``get_scheduled_for_deletion``."""

    def setUp(self):
        self.t = Tournament.objects.create(
            slug='sched', name='Schedule Test', active=True,
        )
        Tournament.objects.filter(pk=self.t.pk).update(
            created_at=timezone.now() - timedelta(days=200),
        )
        self.t.refresh_from_db()

    def tearDown(self):
        TournamentDeletionLog.objects.all().delete()
        Tournament.objects.all().delete()

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=0)
    def test_schedule_sets_deletion_date(self):
        schedule_eligible(retention_days=90, dry_run=False)
        self.t.refresh_from_db()
        self.assertIsNotNone(self.t.scheduled_for_deletion_at)

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=0)
    def test_schedule_creates_audit_log(self):
        schedule_eligible(retention_days=90, dry_run=False)
        self.assertTrue(
            TournamentDeletionLog.objects.filter(
                tournament_id=self.t.pk,
                status=TournamentDeletionLog.Status.SCHEDULED,
            ).exists()
        )

    def test_dry_run_does_not_schedule(self):
        schedule_eligible(retention_days=90, dry_run=True)
        self.t.refresh_from_db()
        self.assertIsNone(self.t.scheduled_for_deletion_at)

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=0)
    def test_scheduled_tournament_is_found(self):
        schedule_eligible(retention_days=90, dry_run=False)
        ready = get_scheduled_for_deletion()
        self.assertIn(self.t, ready)

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=48)
    def test_grace_period_delays_deletion(self):
        schedule_eligible(retention_days=90, dry_run=False)
        ready = get_scheduled_for_deletion()
        self.assertNotIn(self.t, ready)


class ExporterTestCase(TestCase):
    """Tests for multi-CSV zip exporter."""

    def setUp(self):
        self.t = Tournament.objects.create(
            slug='export-test', name='Export Test', active=True,
        )
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        Tournament.objects.all().delete()
        # Clean up temp files
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_zip_is_created(self):
        path = export_tournament_csv_zip(
            self.t,
            output_path=os.path.join(self.tmpdir, 'test.zip'),
        )
        self.assertTrue(os.path.isfile(path))

    def test_zip_contains_manifest(self):
        path = export_tournament_csv_zip(
            self.t,
            output_path=os.path.join(self.tmpdir, 'test.zip'),
        )
        with zipfile.ZipFile(path, 'r') as zf:
            self.assertIn('_manifest.json', zf.namelist())

    def test_zip_contains_tournament_csv(self):
        path = export_tournament_csv_zip(
            self.t,
            output_path=os.path.join(self.tmpdir, 'test.zip'),
        )
        with zipfile.ZipFile(path, 'r') as zf:
            self.assertIn('tournament.csv', zf.namelist())

    def test_zip_contains_all_tables(self):
        path = export_tournament_csv_zip(
            self.t,
            output_path=os.path.join(self.tmpdir, 'test.zip'),
        )
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()
            for expected in [
                'tournament.csv', 'rounds.csv', 'teams.csv',
                'speakers.csv', 'adjudicators.csv', 'venues.csv',
                'debates.csv', 'motions.csv', 'ballots.csv',
                'feedback.csv', 'break_categories.csv',
            ]:
                self.assertIn(expected, names)

    def test_tournament_csv_has_header_row(self):
        path = export_tournament_csv_zip(
            self.t,
            output_path=os.path.join(self.tmpdir, 'test.zip'),
        )
        with zipfile.ZipFile(path, 'r') as zf:
            content = zf.read('tournament.csv').decode('utf-8')
            lines = content.strip().split('\n')
            self.assertGreaterEqual(len(lines), 1)
            self.assertIn('id', lines[0])
            self.assertIn('name', lines[0])


class RetentionCycleTestCase(TestCase):
    """Integration test for the full retention cycle."""

    def setUp(self):
        self.t = Tournament.objects.create(
            slug='cycle-test', name='Cycle Test', active=True,
        )
        Tournament.objects.filter(pk=self.t.pk).update(
            created_at=timezone.now() - timedelta(days=200),
        )
        self.t.refresh_from_db()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        TournamentDeletionLog.objects.all().delete()
        Tournament.objects.all().delete()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @override_settings(
        TOURNAMENT_RETENTION_GRACE_HOURS=0,
        MEDIA_ROOT=None,  # will be overridden below
    )
    def test_full_cycle_deletes_tournament(self):
        with self.settings(MEDIA_ROOT=self.tmpdir):
            run_retention_cycle(
                retention_days=90,
                mode='EXPORT_THEN_DELETE',
                dry_run=False,
            )
        self.assertFalse(Tournament.objects.filter(pk=self.t.pk).exists())

    @override_settings(
        TOURNAMENT_RETENTION_GRACE_HOURS=0,
    )
    def test_full_cycle_creates_deleted_log(self):
        with self.settings(MEDIA_ROOT=self.tmpdir):
            run_retention_cycle(
                retention_days=90,
                mode='EXPORT_THEN_DELETE',
                dry_run=False,
            )
        self.assertTrue(
            TournamentDeletionLog.objects.filter(
                tournament_id=self.t.pk,
                status=TournamentDeletionLog.Status.DELETED,
            ).exists()
        )

    def test_dry_run_preserves_tournament(self):
        run_retention_cycle(
            retention_days=90,
            mode='DELETE_ONLY',
            dry_run=True,
        )
        self.assertTrue(Tournament.objects.filter(pk=self.t.pk).exists())

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=0)
    def test_export_dir_override(self):
        """Archives should be written to the specified directory."""
        export_dir = os.path.join(self.tmpdir, 'custom-export')
        with self.settings(MEDIA_ROOT=self.tmpdir):
            run_retention_cycle(
                retention_days=90,
                mode='EXPORT_THEN_DELETE',
                dry_run=False,
                export_dir=export_dir,
            )
        self.assertTrue(os.path.isdir(export_dir))
        zips = [f for f in os.listdir(export_dir) if f.endswith('.zip')]
        self.assertGreaterEqual(len(zips), 1)

    @override_settings(TOURNAMENT_RETENTION_GRACE_HOURS=0)
    def test_export_failure_prevents_deletion(self):
        """If the export fails, the tournament must NOT be deleted."""
        with self.settings(MEDIA_ROOT='/nonexistent/impossible/path'):
            run_retention_cycle(
                retention_days=90,
                mode='EXPORT_THEN_DELETE',
                dry_run=False,
            )
        # Tournament should still exist (export failed → no deletion)
        self.assertTrue(Tournament.objects.filter(pk=self.t.pk).exists())
        # Failure should be logged
        self.assertTrue(
            TournamentDeletionLog.objects.filter(
                tournament_id=self.t.pk,
                status=TournamentDeletionLog.Status.FAILED,
            ).exists()
        )


class PurgeCommandTestCase(TestCase):
    """Tests for the ``purge_tournaments`` management command."""

    def setUp(self):
        self.t = Tournament.objects.create(
            slug='cmd-test', name='Command Test', active=True,
        )
        Tournament.objects.filter(pk=self.t.pk).update(
            created_at=timezone.now() - timedelta(days=200),
        )
        self.t.refresh_from_db()

    def tearDown(self):
        TournamentDeletionLog.objects.all().delete()
        Tournament.objects.all().delete()

    def test_command_dry_run(self):
        out = StringIO()
        call_command(
            'purge_tournaments',
            '--dry-run',
            '--retention-days', '90',
            '--mode', 'delete',
            stdout=out,
        )
        self.assertTrue(Tournament.objects.filter(pk=self.t.pk).exists())
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
