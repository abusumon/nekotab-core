from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ParticipantTag(models.Model):
    """Custom labels for grouping participants."""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#7c3aed',
        help_text=_("Hex color code for the tag badge"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = _("participant tag")
        verbose_name_plural = _("participant tags")

    def __str__(self):
        return self.name


class ParticipantProfile(models.Model):
    """
    Unified CRM record keyed by email.

    Aggregates identity across Speaker, Adjudicator, and auth.User records so
    the admin has a single view of every person who has interacted with NekoTab.
    """
    ROLE_DEBATER = 'debater'
    ROLE_ADJUDICATOR = 'adjudicator'
    ROLE_TAB_DIRECTOR = 'tab_director'
    ROLE_HYBRID = 'hybrid'
    ROLE_CHOICES = [
        (ROLE_DEBATER, _('Debater')),
        (ROLE_ADJUDICATOR, _('Adjudicator')),
        (ROLE_TAB_DIRECTOR, _('Tab Director')),
        (ROLE_HYBRID, _('Hybrid')),
    ]

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=200)
    primary_role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)

    # Optional link to auth.User (tab directors or participants with accounts)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='participant_profile',
    )

    # Cached activity stats — refreshed by populate_participant_crm command
    tournaments_participated = models.ManyToManyField(
        'tournaments.Tournament', blank=True,
        related_name='crm_participants',
    )
    total_rounds_debated = models.PositiveIntegerField(default=0)
    total_rounds_adjudicated = models.PositiveIntegerField(default=0)

    # Email preferences
    email_subscribed = models.BooleanField(default=True, db_index=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(null=True, blank=True, db_index=True)
    source_tournament = models.ForeignKey(
        'tournaments.Tournament', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='first_seen_participants',
    )

    tags = models.ManyToManyField(ParticipantTag, blank=True, related_name='participants')

    class Meta:
        ordering = ['-last_active']
        indexes = [
            models.Index(fields=['primary_role', 'email_subscribed']),
            models.Index(fields=['primary_role', 'last_active']),
        ]
        verbose_name = _("participant profile")
        verbose_name_plural = _("participant profiles")

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def tournament_count(self):
        return self.tournaments_participated.count()

    # ── Unsubscribe tokens (django.core.signing — stateless, secure) ──

    def generate_unsubscribe_token(self):
        return signing.dumps({'email': self.email, 'pk': self.pk}, salt='crm-unsub')

    @staticmethod
    def verify_unsubscribe_token(token, max_age=86400 * 365):
        """Verify and decode an unsubscribe token. Valid for 1 year."""
        try:
            return signing.loads(token, salt='crm-unsub', max_age=max_age)
        except (signing.BadSignature, signing.SignatureExpired):
            return None


class CampaignAudience(models.Model):
    """Target audience segment for an email campaign.

    When attached to an EmailCampaign, resolve_recipients() returns the set of
    subscribed ParticipantProfiles that match the configured filters.  If no
    CampaignAudience exists for a campaign, the legacy "send to all users"
    behaviour is used.
    """
    campaign = models.OneToOneField(
        'campaigns.EmailCampaign',
        on_delete=models.CASCADE,
        related_name='audience',
    )
    roles = models.JSONField(
        default=list, blank=True,
        help_text=_("Filter by roles, e.g. ['debater', 'adjudicator']"),
    )
    tournament_filter = models.ForeignKey(
        'tournaments.Tournament', null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    tag_filter = models.ManyToManyField(ParticipantTag, blank=True)
    active_since = models.DateField(
        null=True, blank=True,
        help_text=_("Only include participants active since this date"),
    )
    custom_emails = models.TextField(
        blank=True,
        help_text=_("Additional email addresses, one per line"),
    )

    class Meta:
        verbose_name = _("campaign audience")
        verbose_name_plural = _("campaign audiences")

    def __str__(self):
        return f"Audience for {self.campaign.name}"

    def resolve_recipients(self):
        """Return a queryset of subscribed ParticipantProfiles matching this audience."""
        qs = ParticipantProfile.objects.filter(email_subscribed=True)
        if self.roles:
            qs = qs.filter(primary_role__in=self.roles)
        if self.tournament_filter_id:
            qs = qs.filter(tournaments_participated=self.tournament_filter)
        if self.pk and self.tag_filter.exists():
            qs = qs.filter(tags__in=self.tag_filter.all()).distinct()
        if self.active_since:
            qs = qs.filter(last_active__date__gte=self.active_since)
        return qs

    def recipient_count(self):
        count = self.resolve_recipients().count()
        if self.custom_emails:
            count += len([e for e in self.custom_emails.splitlines() if e.strip()])
        return count
