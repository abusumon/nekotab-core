import csv
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    help = 'Import tab directors from a CSV file into the Participant CRM'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

    def handle(self, *args, **options):
        from participant_crm.models import ParticipantProfile
        created = updated = skipped = 0
        errors = []

        with open(options['csv_path'], encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.stdout.write(f'Processing {len(rows)} rows...')

        for row in rows:
            email = row.get('email', '').strip().lower()
            if not email or email == 'abusumon1701@gmail.com':
                skipped += 1
                continue

            tournaments_str = row.get('tournaments', '')
            name_raw = tournaments_str.split('|')[0].strip().strip('"').strip() if tournaments_str else ''
            name = name_raw[:200] if name_raw else email.split('@')[0][:200]

            try:
                profile, was_created = ParticipantProfile.objects.get_or_create(
                    email=email,
                    defaults={
                        'name': name,
                        'primary_role': ParticipantProfile.ROLE_TAB_DIRECTOR,
                        'last_active': timezone.now(),
                    }
                )
                if was_created:
                    created += 1
                else:
                    # Existing profile — promote to hybrid if they were debater/adj
                    if profile.primary_role not in (
                        ParticipantProfile.ROLE_TAB_DIRECTOR,
                        ParticipantProfile.ROLE_HYBRID,
                    ):
                        profile.primary_role = ParticipantProfile.ROLE_HYBRID
                        profile.save(update_fields=['primary_role'])
                    updated += 1
            except Exception as e:
                errors.append(f'{email}: {e}')
                self.stderr.write(f'ERROR {email}: {e}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {created}, Updated (existing): {updated}, Skipped: {skipped}'
        ))
        if errors:
            self.stdout.write(self.style.WARNING(f'Errors: {len(errors)}'))

        from django.db.models import Count
        breakdown = ParticipantProfile.objects.values('primary_role').annotate(n=Count('pk'))
        for row in breakdown:
            self.stdout.write(f"  {row['primary_role']}: {row['n']}")
        self.stdout.write(f"  TOTAL: {ParticipantProfile.objects.count()}")
