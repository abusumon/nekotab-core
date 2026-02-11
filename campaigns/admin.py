from django.contrib import admin
from .models import EmailCampaign, CampaignRecipient, EmailTemplate


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'status', 'total_recipients', 'successful_sends', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['id', 'created_at', 'updated_at', 'sent_at', 'total_recipients', 'successful_sends', 'failed_sends']


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ['email', 'campaign', 'status', 'sent_at']
    list_filter = ['status', 'campaign']
    search_fields = ['email']
    readonly_fields = ['id', 'sent_at']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
