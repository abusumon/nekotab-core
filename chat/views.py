import logging
import secrets

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from tournaments.models import Tournament

from .models import ChatRoom, Message, RoomSession

logger = logging.getLogger(__name__)

VALID_ROOM_TYPES = {rt.value for rt in ChatRoom.RoomType}


def _get_tournament_or_404(tournament_slug):
    return get_object_or_404(Tournament, slug=tournament_slug)


def _get_room_or_404(tournament, room_type):
    if room_type not in VALID_ROOM_TYPES:
        raise Http404
    return get_object_or_404(ChatRoom, tournament=tournament, room_type=room_type, is_active=True)


def _session_has_access(request, room):
    sk = request.session.session_key
    if not sk:
        return False
    return RoomSession.objects.filter(session_key=sk, room=room).exists()


class ChatRoomView(View):
    """Renders the chat room if the session has unlocked the PIN; otherwise shows PIN entry."""

    def get(self, request, tournament_slug, room_type):
        tournament = _get_tournament_or_404(tournament_slug)
        room = _get_room_or_404(tournament, room_type)

        if not _session_has_access(request, room):
            return render(request, 'chat/room_locked.html', {
                'tournament': tournament,
                'room': room,
                'room_type': room_type,
            })

        return render(request, 'chat/room.html', {
            'tournament': tournament,
            'room': room,
            'room_type': room_type,
            'room_label': room.get_room_type_display(),
        })


class ChatPinVerifyView(View):
    """POST: verify PIN; on success grant session access and redirect to the room."""

    def post(self, request, tournament_slug, room_type):
        tournament = _get_tournament_or_404(tournament_slug)
        room = _get_room_or_404(tournament, room_type)

        entered_pin = (request.POST.get('pin') or '').strip()
        if not entered_pin:
            messages.error(request, _("Please enter the PIN."))
            return redirect('chat:chat-room', tournament_slug=tournament_slug, room_type=room_type)

        if entered_pin != room.pin:
            messages.error(request, _("Incorrect PIN. Please try again."))
            return redirect('chat:chat-room', tournament_slug=tournament_slug, room_type=room_type)

        if not request.session.session_key:
            request.session.create()
        RoomSession.objects.get_or_create(
            session_key=request.session.session_key,
            room=room,
        )
        return redirect('chat:chat-room', tournament_slug=tournament_slug, room_type=room_type)


class ChatManageView(LoginRequiredMixin, View):
    """Tab director management: view/change PINs, purge history, toggle rooms."""

    def _check_access(self, request, tournament):
        if request.user.is_superuser:
            return True
        from organizations.models import OrganizationMembership
        if tournament.organization_id:
            return OrganizationMembership.objects.filter(
                user=request.user,
                organization_id=tournament.organization_id,
                role__in=[
                    OrganizationMembership.Role.OWNER,
                    OrganizationMembership.Role.ADMIN,
                    OrganizationMembership.Role.TABMASTER,
                ],
            ).exists()
        return False

    def get(self, request, tournament_slug):
        tournament = _get_tournament_or_404(tournament_slug)
        if not self._check_access(request, tournament):
            raise Http404
        rooms = ChatRoom.objects.filter(tournament=tournament).order_by('room_type')
        return render(request, 'chat/manage.html', {
            'tournament': tournament,
            'rooms': rooms,
        })

    def post(self, request, tournament_slug):
        tournament = _get_tournament_or_404(tournament_slug)
        if not self._check_access(request, tournament):
            raise Http404

        action = request.POST.get('action')
        room_type = request.POST.get('room_type')
        if room_type not in VALID_ROOM_TYPES:
            messages.error(request, _("Invalid room type."))
            return redirect('chat:chat-manage', tournament_slug=tournament_slug)

        room = get_object_or_404(ChatRoom, tournament=tournament, room_type=room_type)

        if action == 'regenerate_pin':
            room.pin = secrets.token_hex(3).upper()
            room.save()
            RoomSession.objects.filter(room=room).delete()
            messages.success(request, _("PIN regenerated. All active sessions have been invalidated."))

        elif action == 'set_pin':
            new_pin = (request.POST.get('new_pin') or '').strip()
            if not new_pin or len(new_pin) < 4:
                messages.error(request, _("PIN must be at least 4 characters."))
                return redirect('chat:chat-manage', tournament_slug=tournament_slug)
            room.pin = new_pin
            room.save()
            RoomSession.objects.filter(room=room).delete()
            messages.success(request, _("PIN updated. All active sessions have been invalidated."))

        elif action == 'purge_history':
            count, _ = Message.objects.filter(room=room).delete()
            messages.success(request, _("%(count)s message(s) deleted.") % {'count': count})

        elif action == 'toggle_room':
            room.is_active = not room.is_active
            room.save()
            state = _("enabled") if room.is_active else _("disabled")
            messages.success(request, _("Room %(state)s.") % {'state': state})

        return redirect('chat:chat-manage', tournament_slug=tournament_slug)


class ChatHistoryView(View):
    """JSON API: last 50 messages (requires session PIN unlock)."""

    def get(self, request, tournament_slug, room_type):
        tournament = _get_tournament_or_404(tournament_slug)
        room = _get_room_or_404(tournament, room_type)

        if not _session_has_access(request, room):
            return JsonResponse({'error': 'Not authorized'}, status=403)

        qs = room.messages.select_related('user').order_by('-created_at')[:50]
        data = [
            {
                'id': m.pk,
                'display_name': m.display_name,
                'content': m.content,
                'timestamp': m.created_at.strftime('%H:%M'),
            }
            for m in reversed(list(qs))
        ]
        return JsonResponse({'messages': data})
