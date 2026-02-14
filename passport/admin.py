from django.contrib import admin
from .models import (
    DebatePassport, TournamentParticipation, RoundPerformance,
    JudgeBallot, Partnership, UserStats,
)


class TournamentParticipationInline(admin.TabularInline):
    model = TournamentParticipation
    extra = 0
    fields = ('tournament_name', 'tournament_format', 'year', 'role', 'broke', 'final_rank')


class UserStatsInline(admin.StackedInline):
    model = UserStats
    extra = 0


@admin.register(DebatePassport)
class DebatePassportAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'country', 'institution',
                    'primary_format', 'experience_level', 'is_public')
    list_filter = ('primary_format', 'experience_level', 'is_public',
                   'is_speaker', 'is_judge', 'is_ca')
    search_fields = ('display_name', 'user__username', 'country', 'institution')
    inlines = [TournamentParticipationInline, UserStatsInline]


class RoundPerformanceInline(admin.TabularInline):
    model = RoundPerformance
    extra = 0
    fields = ('round_number', 'side', 'position', 'result', 'speaker_score')


class JudgeBallotInline(admin.TabularInline):
    model = JudgeBallot
    extra = 0
    fields = ('round_number', 'was_chair', 'panel_size', 'agreed_with_majority')


@admin.register(TournamentParticipation)
class TournamentParticipationAdmin(admin.ModelAdmin):
    list_display = ('passport', 'tournament_name', 'year', 'role', 'broke', 'final_rank')
    list_filter = ('role', 'broke', 'tournament_format', 'year')
    search_fields = ('tournament_name', 'passport__display_name')
    inlines = [RoundPerformanceInline, JudgeBallotInline]


@admin.register(RoundPerformance)
class RoundPerformanceAdmin(admin.ModelAdmin):
    list_display = ('participation', 'round_number', 'side', 'result', 'speaker_score')
    list_filter = ('result', 'side')


@admin.register(JudgeBallot)
class JudgeBallotAdmin(admin.ModelAdmin):
    list_display = ('participation', 'round_number', 'was_chair', 'panel_size', 'agreed_with_majority')
    list_filter = ('was_chair',)


@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    list_display = ('passport', 'partner_name', 'tournaments_together', 'win_rate')
    search_fields = ('passport__display_name', 'partner_name')


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('passport', 'total_tournaments', 'average_speaker_score',
                    'overall_win_rate', 'break_rate', 'last_computed')
    search_fields = ('passport__display_name',)
