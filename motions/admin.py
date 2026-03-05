from django.contrib import admin

from utils.admin import ModelAdmin, TabbycatModelAdminFieldsMixin
from utils.admin_tenant import TournamentScopedAdminMixin

from .models import DebateTeamMotionPreference, Motion, RoundMotion


# ==============================================================================
# Motions
# ==============================================================================

@admin.register(Motion)
class MotionAdmin(TournamentScopedAdminMixin, TabbycatModelAdminFieldsMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('reference', 'text')
    list_filter = ('rounds',)


@admin.register(DebateTeamMotionPreference)
class DebateTeamMotionPreferenceAdmin(TournamentScopedAdminMixin, TabbycatModelAdminFieldsMixin, ModelAdmin):
    tournament_lookup = 'motion__tournament'
    list_display = ('ballot_submission', 'get_confirmed', 'get_team',
                    'get_team_side', 'preference', 'get_motion_ref')
    search_fields = ('motion__reference',)


@admin.register(RoundMotion)
class RoundMotionAdmin(TournamentScopedAdminMixin, TabbycatModelAdminFieldsMixin, ModelAdmin):
    tournament_lookup = 'round__tournament'
    list_display = ('seq', 'round', 'motion')
    list_filter = ('round', 'motion')
    ordering = ('round__seq', 'seq')
