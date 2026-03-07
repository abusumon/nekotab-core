from django.contrib import admin

from utils.admin_tenant import OrganizationScopedAdminMixin

from .models import Organization, OrganizationMembership


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    raw_id_fields = ('user',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_workspace_enabled', 'created_at', 'member_count')
    list_filter = ('is_workspace_enabled',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationMembershipInline]

    def member_count(self, obj):
        return obj.memberships.count()
    member_count.short_description = 'Members'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        from .models import OrganizationMembership as OM
        org_ids = OM.objects.filter(
            user=request.user,
            role__in=[OM.Role.OWNER, OM.Role.ADMIN],
        ).values_list('organization_id', flat=True)
        return qs.filter(id__in=org_ids)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_view_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_change_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_delete_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'joined_at')
    list_filter = ('role', 'organization')
    search_fields = ('user__username', 'user__email', 'organization__name')
    raw_id_fields = ('user',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        org_ids = OrganizationMembership.objects.filter(
            user=request.user,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).values_list('organization_id', flat=True)
        return qs.filter(organization_id__in=org_ids)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_view_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj.organization,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_change_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj.organization,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_delete_permission(request, obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=obj.organization,
            role__in=[OrganizationMembership.Role.OWNER,
                      OrganizationMembership.Role.ADMIN],
        ).exists()
