"""Management command to audit multi-tenant data integrity.

Usage:
    python manage.py check_tenant_integrity
    python manage.py check_tenant_integrity --fix  # auto-fix safe issues
"""

import sys

from django.core.management.base import BaseCommand
from django.db.models import Count, Q


class Command(BaseCommand):
    help = "Audit multi-tenant data integrity: orphan tournaments, missing owners, duplicates, mismatches."

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='Attempt to auto-fix safe issues (e.g. assign orphans to "Unassigned" org).',
        )

    def handle(self, *args, **options):
        from organizations.models import Organization, OrganizationMembership
        from tournaments.models import Tournament

        fix = options['fix']
        issues = []
        self.stdout.write(self.style.MIGRATE_HEADING("\n═══ Multi-Tenant Integrity Audit ═══\n"))

        # ── Check 1: Tournaments without organization ─────────────────────
        null_org = Tournament.objects.filter(organization__isnull=True)
        count = null_org.count()
        if count:
            issues.append(('CRITICAL', f'{count} tournament(s) without organization'))
            self.stdout.write(self.style.ERROR(f"[CRITICAL] {count} tournament(s) without organization:"))
            for t in null_org.values_list('id', 'slug', 'name'):
                self.stdout.write(f"  id={t[0]}  slug={t[1]}  name={t[2]}")
            if fix:
                unassigned, _ = Organization.objects.get_or_create(
                    slug='unassigned',
                    defaults={'name': 'Unassigned Tournaments'},
                )
                null_org.update(organization=unassigned)
                self.stdout.write(self.style.SUCCESS(f"  → Fixed: assigned to '{unassigned.slug}'"))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All tournaments have an organization."))

        # ── Check 2: Organizations without an OWNER ───────────────────────
        orgs_without_owner = Organization.objects.exclude(
            memberships__role=OrganizationMembership.Role.OWNER,
        )
        count = orgs_without_owner.count()
        if count:
            issues.append(('WARNING', f'{count} organization(s) without an owner'))
            self.stdout.write(self.style.WARNING(f"\n[WARNING] {count} organization(s) without an owner:"))
            for o in orgs_without_owner.values_list('id', 'slug', 'name'):
                self.stdout.write(f"  id={o[0]}  slug={o[1]}  name={o[2]}")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All organizations have at least one owner."))

        # ── Check 3: Duplicate memberships ────────────────────────────────
        dupes = (
            OrganizationMembership.objects
            .values('organization_id', 'user_id')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )
        count = dupes.count()
        if count:
            issues.append(('ERROR', f'{count} duplicate membership(s)'))
            self.stdout.write(self.style.ERROR(f"\n[ERROR] {count} duplicate membership pair(s):"))
            for d in dupes:
                self.stdout.write(
                    f"  org_id={d['organization_id']}  user_id={d['user_id']}  count={d['cnt']}")
            if fix:
                fixed = 0
                for d in dupes:
                    memberships = OrganizationMembership.objects.filter(
                        organization_id=d['organization_id'],
                        user_id=d['user_id'],
                    ).order_by('joined_at')
                    # Keep the first (oldest), delete the rest
                    to_delete = memberships[1:]
                    for m in to_delete:
                        m.delete()
                        fixed += 1
                self.stdout.write(self.style.SUCCESS(f"  → Fixed: removed {fixed} duplicate(s)"))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] No duplicate memberships."))

        # ── Check 4: Owner mismatch (tournament.owner not in its org) ─────
        mismatches = Tournament.objects.filter(
            owner__isnull=False,
            organization__isnull=False,
        ).exclude(
            organization__memberships__user=models_F_owner(),
        )
        # Use raw approach since Django ORM can't easily do F('owner') in exclude
        mismatch_list = []
        for t in Tournament.objects.filter(
            owner__isnull=False, organization__isnull=False,
        ).select_related('owner', 'organization'):
            if not OrganizationMembership.objects.filter(
                organization=t.organization, user=t.owner,
            ).exists():
                mismatch_list.append(t)

        if mismatch_list:
            issues.append(('WARNING', f'{len(mismatch_list)} tournament(s) where owner is not in org'))
            self.stdout.write(self.style.WARNING(
                f"\n[WARNING] {len(mismatch_list)} tournament(s) where owner is not a member of the org:"))
            for t in mismatch_list:
                self.stdout.write(
                    f"  tournament={t.slug}  owner={t.owner.username}  org={t.organization.slug}")
            if fix:
                for t in mismatch_list:
                    OrganizationMembership.objects.get_or_create(
                        organization=t.organization,
                        user=t.owner,
                        defaults={'role': OrganizationMembership.Role.OWNER},
                    )
                self.stdout.write(self.style.SUCCESS(
                    f"  → Fixed: added {len(mismatch_list)} owner(s) to their org"))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All tournament owners are members of their org."))

        # ── Check 5: Orphan orgs (no tournaments) ────────────────────────
        empty_orgs = Organization.objects.annotate(
            t_count=Count('tournaments'),
        ).filter(t_count=0)
        count = empty_orgs.count()
        if count:
            issues.append(('INFO', f'{count} organization(s) with no tournaments'))
            self.stdout.write(self.style.WARNING(
                f"\n[INFO] {count} organization(s) with no tournaments:"))
            for o in empty_orgs.values_list('id', 'slug', 'name'):
                self.stdout.write(f"  id={o[0]}  slug={o[1]}  name={o[2]}")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] All organizations have at least one tournament."))

        # ── Summary ───────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n═══ Summary ═══"))
        if not issues:
            self.stdout.write(self.style.SUCCESS("All checks passed. Tenant integrity is sound.\n"))
        else:
            for severity, msg in issues:
                style = {
                    'CRITICAL': self.style.ERROR,
                    'ERROR': self.style.ERROR,
                    'WARNING': self.style.WARNING,
                    'INFO': self.style.NOTICE,
                }.get(severity, self.style.NOTICE)
                self.stdout.write(style(f"  [{severity}] {msg}"))
            self.stdout.write("")

            critical_count = sum(1 for s, _ in issues if s in ('CRITICAL', 'ERROR'))
            if critical_count:
                self.stdout.write(self.style.ERROR(
                    f"{critical_count} critical/error issue(s) found. "
                    "Resolve before deploying migration 0039.\n"))
                sys.exit(1)
            else:
                self.stdout.write(self.style.WARNING(
                    "Non-critical issues found. Review before proceeding.\n"))


def models_F_owner():
    """Placeholder — not used, see the raw loop approach above."""
    pass
