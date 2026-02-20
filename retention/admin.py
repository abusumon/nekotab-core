from django.contrib import admin

from .models import TournamentDeletionLog


@admin.register(TournamentDeletionLog)
class TournamentDeletionLogAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'status', 'owner_username', 'team_count',
                    'round_count', 'debate_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('slug', 'name', 'owner_username', 'owner_email')
    readonly_fields = ('tournament_id', 'slug', 'name', 'owner_email',
                       'owner_username', 'team_count', 'round_count',
                       'debate_count', 'status', 'archive_path',
                       'error_message', 'created_at')
