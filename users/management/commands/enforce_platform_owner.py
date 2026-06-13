"""Management command: enforce_platform_owner

Audits and optionally fixes the superuser/staff flags in the database so that:

  • Only the designated platform owner(s) retain ``is_superuser=True``.
  • Any other user with ``is_superuser=True`` has that flag removed.
  • Users with ``is_staff=True`` who are not tournament-associated and are not
    the platform owner have that flag removed (opt-in via --fix-staff).

Usage
-----
Dry-run (just print what would change):
    python manage.py enforce_platform_owner

Apply the superuser fix:
    python manage.py enforce_platform_owner --fix

Also clean up orphan is_staff flags:
    python manage.py enforce_platform_owner --fix --fix-staff

Override the owner email at runtime:
    python manage.py enforce_platform_owner --owner-email someone@example.com --fix
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Audit and enforce the platform owner superuser flag."

    def add_arguments(self, parser):
        parser.add_argument(
            '--owner-email',
            default='abusumon1701@gmail.com',
            help="Email address of the platform owner (default: abusumon1701@gmail.com).",
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            default=False,
            help="Apply changes. Without this flag the command is a dry-run.",
        )
        parser.add_argument(
            '--fix-staff',
            action='store_true',
            default=False,
            help="Also strip is_staff=True from users who have no tournament association "
                 "and are not the platform owner (requires --fix).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        owner_email = options['owner_email'].strip().lower()
        dry_run = not options['fix']
        fix_staff = options['fix_staff']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN — no changes will be saved. Pass --fix to apply.\n"
            ))

        # ── Locate the platform owner ────────────────────────────────────
        owner = User.objects.filter(email__iexact=owner_email).first()
        if owner is None:
            raise CommandError(
                f"No user found with email '{owner_email}'. "
                "Check the email or create the account first."
            )

        self.stdout.write(f"Platform owner: {owner.username} <{owner.email}>  "
                          f"(pk={owner.pk}, is_superuser={owner.is_superuser})\n")

        if not owner.is_superuser:
            self.stdout.write(self.style.WARNING(
                f"  ⚠  Owner does NOT have is_superuser=True — will grant it."
            ))
            if not dry_run:
                owner.is_superuser = True
                owner.is_staff = True  # is_staff required for Django admin login path
                owner.save(update_fields=['is_superuser', 'is_staff'])
                self.stdout.write(self.style.SUCCESS("  ✓  Granted is_superuser + is_staff to owner."))

        # ── Audit other superusers ───────────────────────────────────────
        other_superusers = (
            User.objects.filter(is_superuser=True)
            .exclude(pk=owner.pk)
        )

        if not other_superusers.exists():
            self.stdout.write(self.style.SUCCESS("\nNo other superusers found. ✓\n"))
        else:
            self.stdout.write(self.style.ERROR(
                f"\nFound {other_superusers.count()} user(s) with is_superuser=True "
                "besides the platform owner:\n"
            ))
            for u in other_superusers:
                self.stdout.write(f"  - {u.username} <{u.email}> (pk={u.pk})")
                if not dry_run:
                    u.is_superuser = False
                    u.save(update_fields=['is_superuser'])
                    self.stdout.write(self.style.SUCCESS("    → is_superuser stripped."))
                else:
                    self.stdout.write("    → would strip is_superuser (dry-run).")

        # ── Audit is_staff users ─────────────────────────────────────────
        staff_users = (
            User.objects.filter(is_staff=True, is_superuser=False)
            .exclude(pk=owner.pk)
        )

        if staff_users.exists():
            self.stdout.write(
                f"\nUsers with is_staff=True (non-owner, non-superuser): "
                f"{staff_users.count()}\n"
            )
            for u in staff_users:
                self.stdout.write(f"  - {u.username} <{u.email}> (pk={u.pk})")

            if fix_staff:
                from django.db.models import Q
                from tournaments.models import Tournament, TournamentStaffMembership
                from organizations.models import OrganizationMembership
                from users.models import Membership

                self.stdout.write(
                    "\nChecking which is_staff users have no tournament association…\n"
                )
                for u in staff_users:
                    has_tournament = (
                        Tournament.objects.filter(owner=u).exists()
                        or OrganizationMembership.objects.filter(user=u).exists()
                        or TournamentStaffMembership.objects.filter(user=u).exists()
                        or Membership.objects.filter(user=u).exists()
                    )
                    if has_tournament:
                        self.stdout.write(
                            f"  {u.username}: has tournament association — keeping is_staff."
                        )
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"  {u.username}: no tournament association — "
                            f"{'stripping' if not dry_run else 'would strip'} is_staff."
                        ))
                        if not dry_run:
                            u.is_staff = False
                            u.save(update_fields=['is_staff'])
            else:
                self.stdout.write(
                    "  (Pass --fix-staff to remove is_staff from users with no "
                    "tournament association.)\n"
                )

        # ── Summary ──────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry-run complete. Re-run with --fix to apply changes."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
