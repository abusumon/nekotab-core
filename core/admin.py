from django.contrib import admin

from .models import SubdomainSlugReservation


@admin.register(SubdomainSlugReservation)
class SubdomainSlugReservationAdmin(admin.ModelAdmin):
    list_display = ('slug', 'tenant_type', 'tournament', 'organization', 'created_at')
    list_filter = ('tenant_type',)
    search_fields = ('slug',)
    raw_id_fields = ('tournament', 'organization')
    readonly_fields = ('created_at',)
