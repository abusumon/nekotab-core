from django.contrib import admin

from .models import Organization, OrganizationMembership


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    raw_id_fields = ('user',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'member_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationMembershipInline]

    def member_count(self, obj):
        return obj.memberships.count()
    member_count.short_description = 'Members'


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'joined_at')
    list_filter = ('role', 'organization')
    search_fields = ('user__username', 'user__email', 'organization__name')
    raw_id_fields = ('user',)
