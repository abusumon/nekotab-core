import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EmailCampaign(models.Model):
    """Model to store email campaigns for promotional emails."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SCHEDULED = 'scheduled', _('Scheduled')
        SENDING = 'sending', _('Sending')
        SENT = 'sent', _('Sent')
        FAILED = 'failed', _('Failed')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text=_("Internal campaign name for your reference")
    )
    subject = models.CharField(
        max_length=200,
        help_text=_("Email subject line")
    )
    preview_text = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Preview text shown in inbox (optional)")
    )
    html_content = models.TextField(
        help_text=_("HTML content of the email")
    )
    plain_text_content = models.TextField(
        blank=True,
        help_text=_("Plain text version (auto-generated if empty)")
    )
    
    # Targeting
    send_to_all = models.BooleanField(
        default=True,
        help_text=_("Send to all users with email addresses")
    )
    
    # Metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Stats
    total_recipients = models.PositiveIntegerField(default=0)
    successful_sends = models.PositiveIntegerField(default=0)
    failed_sends = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Email Campaign")
        verbose_name_plural = _("Email Campaigns")
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def is_editable(self):
        return self.status in [self.Status.DRAFT, self.Status.FAILED]
    
    @property
    def success_rate(self):
        if self.total_recipients == 0:
            return 0
        return round((self.successful_sends / self.total_recipients) * 100, 1)


class CampaignRecipient(models.Model):
    """Track individual email sends for each campaign."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        SENT = 'sent', _('Sent')
        FAILED = 'failed', _('Failed')
        BOUNCED = 'bounced', _('Bounced')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        unique_together = ['campaign', 'email']
    
    def __str__(self):
        return f"{self.email} - {self.campaign.name}"


class EmailTemplate(models.Model):
    """Pre-designed email templates for quick campaign creation."""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    html_content = models.TextField()
    thumbnail = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
