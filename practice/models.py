from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DebateFormat(models.TextChoices):
    BP    = 'bp',    _("British Parliamentary")
    AP    = 'ap',    _("Asian Parliamentary")
    WSDC  = 'wsdc',  _("WSDC")
    MSDC  = 'msdc',  _("MSDC")
    OXFORD = 'oxford', _("Oxford")
    OTHER = 'other', _("Other")


class SessionStatus(models.TextChoices):
    SCHEDULED   = 'scheduled',   _("Scheduled")
    IN_PROGRESS = 'in_progress', _("In Progress")
    COMPLETED   = 'completed',   _("Completed")
    CANCELLED   = 'cancelled',   _("Cancelled")


class ParticipantRole(models.TextChoices):
    DEBATER     = 'debater',     _("Debater")
    ADJUDICATOR = 'adjudicator', _("Adjudicator")


class PracticeSession(models.Model):
    """A single practice debate session organized by a club."""
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='practice_sessions',
        verbose_name=_("organization"),
    )
    title = models.CharField(max_length=200, verbose_name=_("title"))
    date = models.DateField(verbose_name=_("date"))
    start_time = models.TimeField(null=True, blank=True, verbose_name=_("start time"))
    format = models.CharField(
        max_length=20, choices=DebateFormat.choices,
        default=DebateFormat.BP, verbose_name=_("format"),
    )
    venue = models.CharField(max_length=200, blank=True, default='', verbose_name=_("venue"))
    notes = models.TextField(blank=True, default='', verbose_name=_("notes"))
    status = models.CharField(
        max_length=20, choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED, db_index=True, verbose_name=_("status"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_practice_sessions',
        verbose_name=_("created by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'status']),
        ]
        verbose_name = _("practice session")
        verbose_name_plural = _("practice sessions")

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def participant_count(self):
        return self.participants.count()

    @property
    def room_count(self):
        return self.rooms.count()


class SessionRoom(models.Model):
    """A single debate room within a practice session."""
    session = models.ForeignKey(
        PracticeSession,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name=_("session"),
    )
    name = models.CharField(max_length=50, default='Room 1', verbose_name=_("name"))
    motion = models.TextField(blank=True, default='', verbose_name=_("motion"))
    seq = models.PositiveSmallIntegerField(default=1, verbose_name=_("order"))

    class Meta:
        ordering = ['seq']
        unique_together = [['session', 'seq']]
        verbose_name = _("session room")
        verbose_name_plural = _("session rooms")

    def __str__(self):
        return f"{self.session} — {self.name}"


class SessionParticipant(models.Model):
    """A member's participation in a specific practice session."""
    session = models.ForeignKey(
        PracticeSession,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_("session"),
    )
    membership = models.ForeignKey(
        'organizations.OrganizationMembership',
        on_delete=models.CASCADE,
        related_name='session_participations',
        verbose_name=_("member"),
    )
    room = models.ForeignKey(
        SessionRoom,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='participants',
        verbose_name=_("room"),
    )
    role = models.CharField(
        max_length=20, choices=ParticipantRole.choices,
        default=ParticipantRole.DEBATER, verbose_name=_("role"),
    )
    team_name = models.CharField(max_length=100, blank=True, default='', verbose_name=_("team name"))
    attended = models.BooleanField(default=True, verbose_name=_("attended"))

    class Meta:
        unique_together = [['session', 'membership']]
        verbose_name = _("session participant")
        verbose_name_plural = _("session participants")

    def __str__(self):
        return f"{self.membership.user} @ {self.session}"


class SpeakerScore(models.Model):
    """Speaker score for a debater in a practice session room.

    Scores are append-only — ``updated_at`` tracks the last edit, but the
    original submission is never deleted to preserve the audit trail.
    """
    participant = models.OneToOneField(
        SessionParticipant,
        on_delete=models.CASCADE,
        related_name='score',
        verbose_name=_("participant"),
    )
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_("speaker score"),
        help_text=_("Overall speaker score for this debate."),
    )
    reply_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_("reply score"),
    )
    notes = models.TextField(blank=True, default='', verbose_name=_("adjudicator notes"))
    won = models.BooleanField(null=True, blank=True, verbose_name=_("won debate"))
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='submitted_practice_scores',
        verbose_name=_("submitted by"),
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_("submitted at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("speaker score")
        verbose_name_plural = _("speaker scores")

    def __str__(self):
        return f"Score({self.participant}, {self.score})"
