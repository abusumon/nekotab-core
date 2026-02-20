import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class TournamentDeletionLog(models.Model):
    """Audit trail for every tournament processed by the retention system.

    Retained even after the tournament row itself is deleted so operators can
    always answer "what happened to tournament X?"
    """

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _("Scheduled")
        EXPORTED = 'EXPORTED', _("Exported")
        DELETED = 'DELETED', _("Deleted")
        FAILED = 'FAILED', _("Failed")
        SKIPPED = 'SKIPPED', _("Skipped (exempt)")
        DRY_RUN = 'DRY_RUN', _("Dry run")

    tournament_id = models.IntegerField(
        verbose_name=_("tournament ID"),
        help_text=_("PK of the tournament (may no longer exist)."))
    slug = models.CharField(max_length=200,
        verbose_name=_("slug"))
    name = models.CharField(max_length=200,
        verbose_name=_("tournament name"))
    owner_email = models.EmailField(blank=True, default='',
        verbose_name=_("owner email"))
    owner_username = models.CharField(max_length=150, blank=True, default='',
        verbose_name=_("owner username"))

    # Snapshot counts at time of processing
    team_count = models.PositiveIntegerField(default=0)
    round_count = models.PositiveIntegerField(default=0)
    debate_count = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=Status.choices,
        verbose_name=_("status"))
    archive_path = models.CharField(max_length=500, blank=True, default='',
        verbose_name=_("archive path"),
        help_text=_("Path or URL to the exported archive (if any)."))
    error_message = models.TextField(blank=True, default='',
        verbose_name=_("error message"))

    created_at = models.DateTimeField(auto_now_add=True,
        verbose_name=_("created at"))

    class Meta:
        verbose_name = _("tournament deletion log")
        verbose_name_plural = _("tournament deletion logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tournament_id']),
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"[{self.status}] {self.slug} (id={self.tournament_id}) @ {self.created_at}"
