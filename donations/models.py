from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class DonationTransaction(models.Model):
    class DonationType(models.TextChoices):
        ONE_TIME = 'one_time', _('One-Time')
        SUBSCRIPTION = 'subscription', _('Subscription')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        REFUNDED = 'refunded', _('Refunded')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    source = models.CharField(max_length=32, default='lemonsqueezy', db_index=True)
    external_reference = models.CharField(max_length=120, unique=True, db_index=True)
    event_name_last = models.CharField(max_length=100, blank=True)

    donation_type = models.CharField(
        max_length=20,
        choices=DonationType.choices,
        default=DonationType.ONE_TIME,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default='USD', db_index=True)

    donor_name = models.CharField(max_length=200, blank=True)
    donor_email = models.EmailField(blank=True, db_index=True)

    lemon_order_id = models.CharField(max_length=64, blank=True, db_index=True)
    lemon_subscription_id = models.CharField(max_length=64, blank=True, db_index=True)
    lemon_customer_id = models.CharField(max_length=64, blank=True, db_index=True)
    checkout_identifier = models.CharField(max_length=120, blank=True)

    product_name = models.CharField(max_length=255, blank=True)
    variant_name = models.CharField(max_length=255, blank=True)

    donated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metadata = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-donated_at', '-updated_at']
        verbose_name = _('donation transaction')
        verbose_name_plural = _('donation transactions')

    def __str__(self):
        donor = self.donor_email or self.donor_name or 'unknown donor'
        return f"{self.external_reference} - {donor} - {self.amount} {self.currency}"


class LemonWebhookEvent(models.Model):
    payload_hash = models.CharField(max_length=64, unique=True, db_index=True)

    event_name = models.CharField(max_length=100, blank=True, db_index=True)
    lemon_object_type = models.CharField(max_length=100, blank=True)
    lemon_object_id = models.CharField(max_length=64, blank=True, db_index=True)

    signature_valid = models.BooleanField(default=False)
    processed = models.BooleanField(default=False, db_index=True)
    processing_error = models.TextField(blank=True)

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    transaction = models.ForeignKey(
        DonationTransaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='webhook_events',
    )

    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-received_at']
        verbose_name = _('Lemon Squeezy webhook event')
        verbose_name_plural = _('Lemon Squeezy webhook events')

    def __str__(self):
        event = self.event_name or 'unknown-event'
        obj = self.lemon_object_id or 'no-object-id'
        return f"{event} - {obj}"
