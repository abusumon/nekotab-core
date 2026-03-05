from django.contrib import admin

from utils.admin import ModelAdmin
from utils.admin_tenant import TournamentScopedAdminMixin

from .models import BreakCategory, BreakingTeam


# ==============================================================================
# Break Catergories
# ==============================================================================

@admin.register(BreakCategory)
class BreakCategoryAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('name', 'slug', 'seq', 'tournament', 'break_size',
                    'priority', 'is_general', 'rule')
    list_filter = ('tournament', )
    ordering = ('tournament', 'seq')


# ==============================================================================
# Breaking Teams
# ==============================================================================

@admin.register(BreakingTeam)
class BreakingTeamAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'break_category__tournament'
    list_display = ('break_category', 'team', 'rank', 'break_rank', 'remark')
    list_filter = ('break_category__tournament', 'break_category')
    search_fields = ('team__short_name', 'team__long_name',
                     'team__institution__name', 'team__institution__code')
    ordering = ('break_category', )
