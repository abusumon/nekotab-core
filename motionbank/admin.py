from django.contrib import admin
from .models import (
    MotionEntry, MotionAnalysis, MotionStats,
    MotionRating, CaseOutline, CaseOutlineVote, PracticeSession,
)


class MotionAnalysisInline(admin.StackedInline):
    model = MotionAnalysis
    extra = 0


class MotionStatsInline(admin.StackedInline):
    model = MotionStats
    extra = 0


@admin.register(MotionEntry)
class MotionEntryAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'format', 'motion_type', 'difficulty',
                    'tournament_name', 'year', 'region', 'is_approved', 'created_at')
    list_filter = ('format', 'motion_type', 'difficulty', 'prep_type',
                   'is_approved', 'year', 'region')
    search_fields = ('text', 'tournament_name', 'theme_tags')
    prepopulated_fields = {'slug': ('text',)}
    inlines = [MotionAnalysisInline, MotionStatsInline]

    @admin.display(description='Motion')
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text


@admin.register(MotionAnalysis)
class MotionAnalysisAdmin(admin.ModelAdmin):
    list_display = ('motion', 'model_used', 'confidence_score', 'last_updated')
    search_fields = ('motion__text',)


@admin.register(MotionStats)
class MotionStatsAdmin(admin.ModelAdmin):
    list_display = ('motion', 'times_practiced', 'times_used_in_tournaments',
                    'average_rating', 'gov_win_rate')


@admin.register(MotionRating)
class MotionRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'motion', 'score', 'created_at')


@admin.register(CaseOutline)
class CaseOutlineAdmin(admin.ModelAdmin):
    list_display = ('title', 'motion', 'author', 'side', 'upvotes', 'created_at')
    list_filter = ('side',)
    search_fields = ('title', 'content', 'motion__text')


@admin.register(CaseOutlineVote)
class CaseOutlineVoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'case_outline', 'created_at')


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'motion', 'side_practiced', 'duration_minutes', 'created_at')
    list_filter = ('side_practiced',)
