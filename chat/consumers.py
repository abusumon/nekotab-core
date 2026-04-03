import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for tournament chat rooms.

    Connection URL: ws://.../ws/chat/<tournament_slug>/<room_type>/
    Connection is rejected if the session has not unlocked the room PIN.
    """

    async def connect(self):
        self.tournament_slug = self.scope['url_route']['kwargs']['tournament_slug']
        self.room_type = self.scope['url_route']['kwargs']['room_type']
        self.room_group_name = f"chat_{self.tournament_slug}_{self.room_type}"

        # Verify PIN access before accepting
        room = await self.get_room()
        if room is None:
            await self.close(code=4404)
            return

        session = self.scope.get('session')
        session_key = session.session_key if session else None
        if not await self.session_has_access(session_key, room):
            await self.close(code=4403)
            return

        # Accept and join the broadcast group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send last 50 messages as history
        messages = await self.get_recent_messages(room)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')
        if msg_type != 'message':
            return

        content = (data.get('content') or '').strip()
        if not content or len(content) > 2000:
            return

        # Determine display name
        user = self.scope.get('user')
        if user and user.is_authenticated:
            display_name = user.get_full_name() or user.username
        else:
            display_name = (data.get('display_name') or 'Guest').strip()[:100]

        room = await self.get_room()
        if room is None:
            return

        # Persist the message
        saved = await self.save_message(room, user if (user and user.is_authenticated) else None, display_name, content)

        # Broadcast to all group members
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': saved['id'],
                'display_name': display_name,
                'content': content,
                'timestamp': saved['timestamp'],
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'display_name': event['display_name'],
            'content': event['content'],
            'timestamp': event['timestamp'],
        }))

    # ── Database helpers ────────────────────────────────────────────────────

    @database_sync_to_async
    def get_room(self):
        from .models import ChatRoom
        try:
            return ChatRoom.objects.select_related('tournament').get(
                tournament__slug=self.tournament_slug,
                room_type=self.room_type,
                is_active=True,
            )
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def session_has_access(self, session_key, room):
        from .models import RoomSession
        if not session_key:
            return False
        return RoomSession.objects.filter(session_key=session_key, room=room).exists()

    @database_sync_to_async
    def get_recent_messages(self, room):
        from .models import Message
        qs = room.messages.select_related('user').order_by('-created_at')[:50]
        result = []
        for m in reversed(list(qs)):
            result.append({
                'id': m.pk,
                'display_name': m.display_name,
                'content': m.content,
                'timestamp': m.created_at.strftime('%H:%M'),
            })
        return result

    @database_sync_to_async
    def save_message(self, room, user, display_name, content):
        from .models import Message
        m = Message.objects.create(
            room=room,
            user=user,
            display_name=display_name,
            content=content,
        )
        return {'id': m.pk, 'timestamp': m.created_at.strftime('%H:%M')}
