from django.contrib import admin
from .models import PageView, DailyStats, ActiveSession


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['path', 'user', 'ip_address', 'country', 'device_type', 'timestamp']
    list_filter = ['device_type', 'country', 'timestamp']
    search_fields = ['path', 'ip_address', 'user__username']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_views', 'unique_visitors', 'new_signups', 'tournaments_created']
    list_filter = ['date']
    readonly_fields = ['date']


@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'current_path', 'country', 'last_activity']
    list_filter = ['country']
    search_fields = ['session_key', 'user__username']
