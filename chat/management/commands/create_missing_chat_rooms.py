"""Management command: create_missing_chat_rooms

Creates the 3 standard ChatRoom objects (tab / organizers / adjudicators) for
every tournament that does not already have them.  Safe to run multiple times.
"""
import secrets

from django.core.management.base import BaseCommand

from chat.models import ChatRoom
from tournaments.models import Tournament


class Command(BaseCommand):
    help = "Create missing chat rooms (tab / organizers / adjudicators) for all tournaments."

    def add_arguments(self, parser):
        parser.add_argument(
            '--tournament',
            metavar='SLUG',
            help='Limit to a single tournament slug.',
        )

    def handle(self, *args, **options):
        qs = Tournament.objects.all()
        if options['tournament']:
            qs = qs.filter(slug=options['tournament'])

        room_types = [rt.value for rt in ChatRoom.RoomType]
        created_total = 0

        for tournament in qs:
            existing = set(
                ChatRoom.objects.filter(tournament=tournament)
                .values_list('room_type', flat=True)
            )
            for rt in room_types:
                if rt not in existing:
                    pin = secrets.token_hex(3).upper()  # e.g. "A3F7C2"
                    ChatRoom.objects.create(
                        tournament=tournament,
                        room_type=rt,
                        pin=pin,
                    )
                    self.stdout.write(
                        f"  Created [{rt}] room for {tournament.slug!r}  PIN={pin}"
                    )
                    created_total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_total} room(s) created across {qs.count()} tournament(s)."
            )
        )
