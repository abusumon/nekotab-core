"""Backfill allauth EmailAddress records for existing users.

Users created before django-allauth was enabled don't have EmailAddress rows.
Without a *verified* EmailAddress, allauth's ``wipe_password()`` security
measure will destroy the password hash when the user first signs in with
Google.  This command creates verified EmailAddress records for every active
user that is missing one.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from allauth.account.models import EmailAddress

User = get_user_model()


class Command(BaseCommand):
    help = "Create verified allauth EmailAddress records for active users that lack one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be done without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        users = User.objects.filter(is_active=True).exclude(email="")
        created = 0
        updated = 0

        for user in users.iterator():
            existing = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
            if existing is None:
                if not dry_run:
                    EmailAddress.objects.create(
                        user=user,
                        email=user.email,
                        verified=True,
                        primary=True,
                    )
                created += 1
                self.stdout.write(f"  + {user.username} <{user.email}>")
            elif not existing.verified:
                if not dry_run:
                    existing.verified = True
                    existing.save(update_fields=["verified"])
                updated += 1
                self.stdout.write(f"  ~ {user.username} <{user.email}> (marked verified)")

        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {created} EmailAddress record(s), "
                f"verified {updated} existing record(s)."
            )
        )
