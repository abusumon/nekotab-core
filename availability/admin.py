from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from utils.admin import ModelAdmin
from utils.admin_tenant import TournamentScopedAdminMixin

from .models import RoundAvailability


@admin.register(RoundAvailability)
class RoundAvailabilityAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'round__tournament'
    list_display = ('content_object', 'content_type', 'round')
    list_filter = ('content_type__model', 'round')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content_object')


# Used in participants/admin.py and venues/admin.py
class RoundAvailabilityInline(GenericTabularInline):
    model = RoundAvailability
    extra = 1
