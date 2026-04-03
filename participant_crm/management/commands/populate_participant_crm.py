from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from adjallocation.models import DebateAdjudicator
from draw.models import DebateTeam
from participants.models import Adjudicator, Speaker
from participant_crm.models import ParticipantProfile
from tournaments.models import Tournament

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the Participant CRM from Speaker, Adjudicator, and User records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be created/updated without writing to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(self.style.MIGRATE_HEADING('Populating Participant CRM...'))
        if dry_run:
            self.stdout.write(self.style.WARNING('  DRY RUN — no changes will be saved'))

        email_map = {}  # normalised email → profile data dict

        # ── Step 1: Scan speakers ─────────────────────────────────────────
        speakers = (
            Speaker.objects
            .select_related('team__tournament')
            .exclude(Q(email__isnull=True) | Q(email=''))
        )
        speaker_count = 0
        for s in speakers.iterator():
            email = s.email.strip().lower()
            if not email:
                continue
            speaker_count += 1
            entry = email_map.setdefault(email, _empty_entry(s.name))
            entry['is_debater'] = True
            if s.team_id:
                entry['speaker_team_ids'].add(s.team_id)
            tournament = getattr(s.team, 'tournament', None) if s.team else None
            if tournament:
                entry['tournaments'].add(tournament)
                if not entry['source_tournament']:
                    entry['source_tournament'] = tournament
        self.stdout.write(f'  ✓ {speaker_count} speakers with email')

        # ── Step 2: Scan adjudicators ─────────────────────────────────────
        adjs = (
            Adjudicator.objects
            .select_related('tournament')
            .exclude(Q(email__isnull=True) | Q(email=''))
        )
        adj_count = 0
        for a in adjs.iterator():
            email = a.email.strip().lower()
            if not email:
                continue
            adj_count += 1
            entry = email_map.setdefault(email, _empty_entry(a.name))
            entry['is_adjudicator'] = True
            entry['adjudicator_ids'].add(a.pk)
            if a.tournament:
                entry['tournaments'].add(a.tournament)
                if not entry['source_tournament']:
                    entry['source_tournament'] = a.tournament
        self.stdout.write(f'  ✓ {adj_count} adjudicators with email')

        # ── Step 3: Scan users (link accounts + identify tab directors) ───
        tournament_owner_ids = set(
            Tournament.objects
            .exclude(owner__isnull=True)
            .values_list('owner_id', flat=True)
        )
        user_count = 0
        for u in User.objects.exclude(Q(email__isnull=True) | Q(email='')).iterator():
            email = u.email.strip().lower()
            if not email:
                continue
            is_staff = u.is_staff or u.is_superuser or u.pk in tournament_owner_ids
            if email in email_map:
                email_map[email]['user'] = u
                if is_staff:
                    email_map[email]['is_tab_director'] = True
                user_count += 1
            elif is_staff:
                entry = email_map.setdefault(email, _empty_entry(
                    u.get_full_name() or u.username,
                ))
                entry['is_tab_director'] = True
                entry['user'] = u
                user_count += 1
        self.stdout.write(f'  ✓ {user_count} users linked')

        # ── Step 4: Bulk-compute round counts ─────────────────────────────
        team_round_counts = dict(
            DebateTeam.objects
            .values('team_id')
            .annotate(c=Count('id'))
            .values_list('team_id', 'c')
        )
        adj_round_counts = dict(
            DebateAdjudicator.objects
            .values('adjudicator_id')
            .annotate(c=Count('id'))
            .values_list('adjudicator_id', 'c')
        )

        # ── Step 5: Create / update profiles ─────────────────────────────
        now = timezone.now()
        created = updated = 0
        role_counts = defaultdict(int)

        for email, data in email_map.items():
            # Determine primary role
            if data['is_debater'] and data['is_adjudicator']:
                role = ParticipantProfile.ROLE_HYBRID
            elif data['is_debater']:
                role = ParticipantProfile.ROLE_DEBATER
            elif data['is_adjudicator']:
                role = ParticipantProfile.ROLE_ADJUDICATOR
            elif data['is_tab_director']:
                role = ParticipantProfile.ROLE_TAB_DIRECTOR
            else:
                continue

            rounds_debated = sum(
                team_round_counts.get(tid, 0) for tid in data['speaker_team_ids']
            )
            rounds_adjudicated = sum(
                adj_round_counts.get(aid, 0) for aid in data['adjudicator_ids']
            )

            role_counts[role] += 1

            if dry_run:
                created += 1
                continue

            profile, was_created = ParticipantProfile.objects.update_or_create(
                email=email,
                defaults={
                    'name': data['name'],
                    'primary_role': role,
                    'user': data['user'],
                    'total_rounds_debated': rounds_debated,
                    'total_rounds_adjudicated': rounds_adjudicated,
                    'source_tournament': data['source_tournament'],
                    'last_active': now,
                },
            )

            if data['tournaments']:
                profile.tournaments_participated.set(list(data['tournaments']))

            if was_created:
                created += 1
            else:
                updated += 1

        # ── Summary ───────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('CRM Population Complete'))
        self.stdout.write(f'  Created: {created}  |  Updated: {updated}')
        for role_key, label in ParticipantProfile.ROLE_CHOICES:
            self.stdout.write(f'  {label}: {role_counts.get(role_key, 0)}')
        self.stdout.write(f'  Total: {sum(role_counts.values())}')


def _empty_entry(name):
    return {
        'name': name,
        'is_debater': False,
        'is_adjudicator': False,
        'is_tab_director': False,
        'user': None,
        'tournaments': set(),
        'source_tournament': None,
        'speaker_team_ids': set(),
        'adjudicator_ids': set(),
    }
