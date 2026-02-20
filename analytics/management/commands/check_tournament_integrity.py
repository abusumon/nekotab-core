import re
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from tournaments.models import Tournament

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Check tournament data integrity: detect broken slugs, "
        "orphaned data, stale tournaments, and slug/DNS issues."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to auto-fix issues (e.g. normalise slugs)',
        )
        parser.add_argument(
            '--stale-days',
            type=int,
            default=365,
            help='Consider tournaments inactive for this many days as stale (default: 365)',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        stale_days = options['stale_days']
        issues = []

        self.stdout.write(self.style.MIGRATE_HEADING("Tournament Integrity Check"))
        self.stdout.write("=" * 60)

        # ── 1. Check for empty or missing slugs ──────────────────────
        empty_slugs = Tournament.objects.filter(slug='')
        if empty_slugs.exists():
            for t in empty_slugs:
                issues.append(f"CRITICAL: Tournament id={t.id} '{t.name}' has an empty slug")
            self.stdout.write(self.style.ERROR(
                f"[CRITICAL] {empty_slugs.count()} tournament(s) with empty slugs"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] No empty slugs"))

        # ── 2. Check for slugs with underscores (DNS-unsafe) ─────────
        underscore_slugs = Tournament.objects.filter(slug__contains='_')
        if underscore_slugs.exists():
            for t in underscore_slugs:
                issues.append(f"WARNING: Tournament id={t.id} slug='{t.slug}' contains underscores (DNS-unsafe)")
                if fix:
                    new_slug = t.slug.replace('_', '-')
                    if not Tournament.objects.filter(slug=new_slug).exists():
                        old_slug = t.slug
                        t.slug = new_slug
                        t.save(update_fields=['slug'])
                        self.stdout.write(self.style.WARNING(
                            f"  FIXED: '{old_slug}' → '{new_slug}'"
                        ))
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"  CANNOT FIX: '{t.slug}' → '{new_slug}' already exists"
                        ))
            self.stdout.write(self.style.WARNING(
                f"[WARN] {underscore_slugs.count()} tournament(s) with underscores in slug"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] No underscored slugs"))

        # ── 3. Check for slugs starting/ending with hyphens ──────────
        dns_re = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')
        all_tournaments = Tournament.objects.all()
        bad_dns = []
        for t in all_tournaments:
            if t.slug and not dns_re.match(t.slug.lower()):
                bad_dns.append(t)
                issues.append(f"WARNING: Tournament id={t.id} slug='{t.slug}' is not DNS-safe")
        if bad_dns:
            self.stdout.write(self.style.WARNING(
                f"[WARN] {len(bad_dns)} tournament(s) with DNS-unsafe slugs: "
                + ", ".join(f"'{t.slug}'" for t in bad_dns[:10])
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All slugs are DNS-safe"))

        # ── 4. Check for duplicate slugs (case-insensitive) ──────────
        from django.db.models import Count
        from django.db.models.functions import Lower
        dupes = (
            Tournament.objects.annotate(lower_slug=Lower('slug'))
            .values('lower_slug')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )
        if dupes.exists():
            for d in dupes:
                tournaments = Tournament.objects.filter(slug__iexact=d['lower_slug'])
                slugs = [t.slug for t in tournaments]
                issues.append(f"WARNING: Case-insensitive duplicate slugs: {slugs}")
                self.stdout.write(self.style.WARNING(
                    f"  Duplicate (case-insensitive): {slugs}"
                ))
            self.stdout.write(self.style.WARNING(
                f"[WARN] {dupes.count()} case-insensitive slug collision(s)"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] No case-insensitive slug duplicates"))

        # ── 5. Check for tournaments without owners ──────────────────
        no_owner = Tournament.objects.filter(owner__isnull=True)
        if no_owner.exists():
            for t in no_owner:
                issues.append(f"INFO: Tournament id={t.id} slug='{t.slug}' has no owner")
            self.stdout.write(self.style.WARNING(
                f"[INFO] {no_owner.count()} tournament(s) without an owner"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All tournaments have owners"))

        # ── 6. Check for tournaments with no rounds ──────────────────
        no_rounds = Tournament.objects.annotate(
            round_count=Count('round')
        ).filter(round_count=0)
        if no_rounds.exists():
            for t in no_rounds:
                issues.append(f"INFO: Tournament id={t.id} slug='{t.slug}' has no rounds")
            self.stdout.write(self.style.WARNING(
                f"[INFO] {no_rounds.count()} tournament(s) with zero rounds"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All tournaments have at least one round"))

        # ── 7. Check for stale tournaments ────────────────────────────
        cutoff = timezone.now() - timedelta(days=stale_days)
        stale = Tournament.objects.filter(
            active=True,
            created_at__lt=cutoff,
        ).annotate(
            round_count=Count('round'),
        )
        stale_count = stale.count()
        if stale_count:
            self.stdout.write(self.style.WARNING(
                f"[INFO] {stale_count} active tournament(s) older than {stale_days} days"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"[OK] No active tournaments older than {stale_days} days"
            ))

        # ── Summary ──────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("=" * 60)
        total = Tournament.objects.count()
        self.stdout.write(f"Total tournaments: {total}")
        self.stdout.write(f"Issues found: {len(issues)}")

        if issues:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Issue Details:"))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f"  {i}. {issue}")

        if issues:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Run with --fix to attempt automatic fixes where possible."
            ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Integrity check complete."))
