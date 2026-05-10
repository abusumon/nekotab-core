from django.contrib import admin

from .models import DonationTransaction, LemonWebhookEvent


@admin.register(DonationTransaction)
class DonationTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'external_reference',
        'status',
        'donation_type',
        'amount',
        'currency',
        'donor_email',
        'donated_at',
    )
    list_filter = ('status', 'donation_type', 'currency', 'source')
    search_fields = (
        'external_reference',
        'donor_email',
        'donor_name',
        'lemon_order_id',
        'lemon_subscription_id',
    )
    readonly_fields = ('first_seen_at', 'updated_at', 'raw_payload', 'metadata')
    date_hierarchy = 'donated_at'


@admin.register(LemonWebhookEvent)
class LemonWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        'event_name',
        'lemon_object_type',
        'lemon_object_id',
        'signature_valid',
        'processed',
        'received_at',
    )
    list_filter = ('signature_valid', 'processed', 'event_name')
    search_fields = ('event_name', 'lemon_object_id', 'payload_hash', 'processing_error')
    readonly_fields = ('payload_hash', 'payload', 'received_at', 'processed_at', 'processing_error')
