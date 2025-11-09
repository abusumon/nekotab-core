from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from tournaments.models import Tournament


class Command(BaseCommand):
    help = "Backfill Tournament.owner for tournaments where it's null. Optionally limit to a comma-separated slug list."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Username to assign as owner')
        parser.add_argument('--slugs', default='', help='Comma-separated list of tournament slugs to limit the operation')
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        slugs_arg = options['slugs']
        dry = options['dry_run']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        qs = Tournament.objects.filter(owner__isnull=True)
        if slugs_arg:
            slugs = [s.strip() for s in slugs_arg.split(',') if s.strip()]
            qs = qs.filter(slug__in=slugs)

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No tournaments with null owner to update.'))
            return

        self.stdout.write(f"Found {count} tournaments with null owner.")

        for t in qs:
            self.stdout.write(f" - {t.slug}: assigning to {user.username}")
            if not dry:
                t.owner = user
                t.save(update_fields=['owner'])

        if dry:
            self.stdout.write(self.style.WARNING('Dry run complete. No changes were saved.'))
        else:
            self.stdout.write(self.style.SUCCESS('Owner backfill complete.'))
