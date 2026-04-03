from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ChatRoom(models.Model):
    """One of 3 PIN-protected chat rooms per tournament."""

    class RoomType(models.TextChoices):
        TAB          = 'tab',          _("Tab Room")
        ORGANIZERS   = 'organizers',   _("Organizers")
        ADJUDICATORS = 'adjudicators', _("Adjudicators")

    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        verbose_name=_("tournament"),
    )
    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        verbose_name=_("room type"),
    )
    pin = models.CharField(
        max_length=10,
        verbose_name=_("PIN"),
        help_text=_("Required to enter this room. Share only with intended participants."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("chat room")
        verbose_name_plural = _("chat rooms")
        unique_together = [('tournament', 'room_type')]

    def __str__(self):
        return f"{self.tournament.slug} / {self.get_room_type_display()}"


class Message(models.Model):
    """A single chat message inside a room."""

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_("room"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chat_messages',
        verbose_name=_("user"),
    )
    display_name = models.CharField(max_length=100, verbose_name=_("display name"))
    content = models.TextField(verbose_name=_("content"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.room}] {self.display_name}: {self.content[:50]}"


class RoomSession(models.Model):
    """Records that a session has successfully entered a room's PIN."""

    session_key = models.CharField(max_length=40, db_index=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_("room"),
    )
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("room session")
        verbose_name_plural = _("room sessions")
        unique_together = [('session_key', 'room')]

    def __str__(self):
        return f"{self.session_key[:8]}… → {self.room}"
