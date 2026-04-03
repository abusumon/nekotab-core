from django.contrib import admin
from .models import CampaignAudience, ParticipantProfile, ParticipantTag


@admin.register(ParticipantProfile)
class ParticipantProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'primary_role', 'total_rounds_debated',
                    'total_rounds_adjudicated', 'email_subscribed', 'last_active']
    list_filter = ['primary_role', 'email_subscribed']
    search_fields = ['name', 'email']
    readonly_fields = ['first_seen']
    raw_id_fields = ['user', 'source_tournament']


@admin.register(ParticipantTag)
class ParticipantTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_at']


@admin.register(CampaignAudience)
class CampaignAudienceAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'roles', 'active_since']
    raw_id_fields = ['campaign', 'tournament_filter']
