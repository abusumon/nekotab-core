from django.contrib import admin

from utils.admin import ModelAdmin
from utils.admin_tenant import TournamentScopedAdminMixin, get_admin_tournaments_for_user

from .models import (
    Round,
    ScheduleEvent,
    Tournament,
    TournamentAuditLog,
    TournamentMetadata,
    TournamentStaffInvitation,
    TournamentStaffMembership,
)


# ==============================================================================
# Tournament
# ==============================================================================

@admin.register(Tournament)
class TournamentAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'seq', 'short_name', 'current_round',
                    'active', 'is_listed', 'retention_exempt')
    list_filter = ('active', 'is_listed', 'retention_exempt')
    ordering = ('seq', )

    def _get_allowed_tournament_ids(self, request):
        cache_attr = '_admin_allowed_tournament_ids'
        ids = getattr(request, cache_attr, None)
        if ids is not None:
            return ids
        ids = list(
            get_admin_tournaments_for_user(request.user)
            .values_list('id', flat=True)
        )
        setattr(request, cache_attr, ids)
        return ids

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id__in=self._get_allowed_tournament_ids(request))

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_view_permission(request, obj)
        return obj.id in self._get_allowed_tournament_ids(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_change_permission(request, obj)
        return obj.id in self._get_allowed_tournament_ids(request)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_delete_permission(request, obj)
        return obj.id in self._get_allowed_tournament_ids(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            from organizations.models import Organization, OrganizationMembership
            if db_field.related_model is Organization:
                org_ids = OrganizationMembership.objects.filter(
                    user=request.user,
                    role__in=[
                        OrganizationMembership.Role.OWNER,
                        OrganizationMembership.Role.ADMIN,
                    ],
                ).values_list('organization_id', flat=True)
                kwargs['queryset'] = Organization.objects.filter(id__in=org_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ==============================================================================
# Round
# ==============================================================================

@admin.register(Round)
class RoundAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('name', 'tournament', 'seq', 'abbreviation', 'stage',
                    'draw_type', 'draw_status', 'feedback_weight', 'silent',
                    'motions_released', 'starts_at', 'completed')
    list_editable = ('feedback_weight', 'silent', 'motions_released', 'completed')
    list_filter = ('tournament', )
    search_fields = ('name', 'seq', 'abbreviation', 'stage', 'draw_type', 'draw_status')
    ordering = ('tournament__slug', 'seq')


@admin.register(ScheduleEvent)
class ScheduleEventAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('tournament', 'title', 'type', 'start_time', 'end_time', 'round')
    list_filter = ('tournament', 'type')
    search_fields = ('title',)
    ordering = ('tournament', 'start_time')


@admin.register(TournamentMetadata)
class TournamentMetadataAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = (
        'tournament', 'status', 'visibility', 'registration_type',
        'event_start_date', 'event_end_date',
    )
    list_filter = ('status', 'visibility', 'registration_type')
    search_fields = ('tournament__name', 'tournament__slug', 'event_format', 'venue')


@admin.register(TournamentStaffMembership)
class TournamentStaffMembershipAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('tournament', 'user', 'role', 'invited_by', 'accepted_at', 'created_at')
    list_filter = ('role', 'accepted_at')
    search_fields = ('tournament__name', 'tournament__slug', 'user__username', 'user__email')


@admin.register(TournamentStaffInvitation)
class TournamentStaffInvitationAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('tournament', 'email', 'role', 'invited_by', 'expires_at', 'accepted_at')
    list_filter = ('role', 'accepted_at')
    search_fields = ('tournament__name', 'tournament__slug', 'email')


@admin.register(TournamentAuditLog)
class TournamentAuditLogAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('tournament', 'actor', 'action', 'entity_type', 'entity_id', 'created_at')
    list_filter = ('entity_type',)
    search_fields = ('tournament__name', 'tournament__slug', 'action', 'entity_type', 'entity_id')
