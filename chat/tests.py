from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from chat.models import ChatRoom, RoomSession
from organizations.models import Organization
from tournaments.models import Tournament


class ChatAccessControlTests(TestCase):

    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(name='Chat Audit Org', slug='chat-audit-org')
        self.tournament = Tournament.objects.create(slug='chat-audit-test', organization=self.organization)
        self.room = ChatRoom.objects.create(
            tournament=self.tournament,
            room_type=ChatRoom.RoomType.TAB,
            pin='ABC123',
        )

    def _pin_verify_url(self):
        return reverse('chat:chat-pin-verify', kwargs={
            'tournament_slug': self.tournament.slug,
            'room_type': self.room.room_type,
        })

    def _history_url(self):
        return reverse('chat:chat-history', kwargs={
            'tournament_slug': self.tournament.slug,
            'room_type': self.room.room_type,
        })

    @override_settings(CHAT_SESSION_TTL_SECONDS=60)
    def test_chat_history_denied_after_room_session_expires(self):
        self.client.post(self._pin_verify_url(), {'pin': self.room.pin})
        self.assertTrue(RoomSession.objects.filter(room=self.room).exists())

        allowed = self.client.get(self._history_url())
        self.assertEqual(allowed.status_code, 200)

        room_session = RoomSession.objects.get(room=self.room)
        room_session.unlocked_at = timezone.now() - timedelta(seconds=61)
        room_session.save(update_fields=['unlocked_at'])

        denied = self.client.get(self._history_url())
        self.assertEqual(denied.status_code, 403)

    @override_settings(CHAT_PIN_MAX_ATTEMPTS=3, CHAT_PIN_LOCKOUT_SECONDS=600)
    def test_correct_pin_rejected_during_lockout_window(self):
        for _ in range(3):
            self.client.post(self._pin_verify_url(), {'pin': 'WRONGPIN'})

        response = self.client.post(self._pin_verify_url(), {'pin': self.room.pin})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(RoomSession.objects.filter(room=self.room).exists())
