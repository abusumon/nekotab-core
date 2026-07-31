from django.core.management.base import BaseCommand
from tournaments.models import Tournament


class Command(BaseCommand):
    help = (
        "One-time backfill: set the email__reply_to_address preference to the "
        "owner's email for every tournament that doesn't already have one set. "
        "Tournaments created before this preference was auto-populated at "
        "creation time fall back to DEFAULT_FROM_EMAIL (support@nekotab.app) "
        "for every participant-facing email, so replies land in the site "
        "owner's inbox instead of the tournament director's."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')

    def handle(self, *args, **options):
        dry = options['dry_run']

        qs = Tournament.objects.filter(owner__isnull=False).exclude(owner__email='').select_related('owner')
        updated = 0
        skipped_has_pref = 0
        skipped_no_email = Tournament.objects.filter(owner__isnull=False, owner__email='').count()
        skipped_no_owner = Tournament.objects.filter(owner__isnull=True).count()

        for t in qs:
            if t.pref('reply_to_address'):
                skipped_has_pref += 1
                continue

            self.stdout.write(f"{'[dry-run] ' if dry else ''}{t.slug}: reply_to_address -> {t.owner.email}")
            if not dry:
                t.preferences['email__reply_to_address'] = t.owner.email
                if not t.pref('reply_to_name'):
                    name = t.owner.get_full_name().strip() or t.owner.username
                    t.preferences['email__reply_to_name'] = name
            updated += 1

        verb = 'Would update' if dry else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {updated} tournament(s). "
            f"{skipped_has_pref} already had a reply-to set, "
            f"{skipped_no_owner} have no owner, "
            f"{skipped_no_email} owners have no email on file."))
