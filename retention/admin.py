import os

from django.contrib import admin
from django.utils.html import format_html

from .models import TournamentDeletionLog


@admin.register(TournamentDeletionLog)
class TournamentDeletionLogAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'status', 'owner_username', 'team_count',
                    'round_count', 'debate_count', 'download_link', 'created_at')
    list_filter = ('status',)
    search_fields = ('slug', 'name', 'owner_username', 'owner_email')
    readonly_fields = ('tournament_id', 'slug', 'name', 'owner_email',
                       'owner_username', 'team_count', 'round_count',
                       'debate_count', 'status', 'archive_path',
                       'error_message', 'created_at', 'download_link')

    @admin.display(description='Archive')
    def download_link(self, obj):
        if not obj.archive_path:
            return '—'
        if not os.path.isfile(obj.archive_path):
            return format_html('<span style="color:#999" title="{}">expired</span>', obj.archive_path)
        return format_html(
            '<a href="/admin/retention/download/{}/">⬇ Download</a>',
            obj.pk,
        )
