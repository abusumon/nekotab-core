from django.contrib import admin
from .models import (
    ForumTag, UserBadge, ForumThread, ForumPost,
    ForumVote, ForumBookmark, ForumReport,
)


@admin.register(ForumTag)
class ForumTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge_type', 'verified', 'awarded_at')
    list_filter = ('badge_type', 'verified')
    search_fields = ('user__username',)


class ForumPostInline(admin.TabularInline):
    model = ForumPost
    extra = 0
    fields = ('author', 'post_type', 'content', 'parent', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'debate_format', 'topic_category', 'skill_level',
                    'view_count', 'is_pinned', 'is_locked', 'created_at')
    list_filter = ('debate_format', 'topic_category', 'skill_level', 'is_pinned', 'is_locked')
    search_fields = ('title', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ForumPostInline]


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'post_type', 'vote_score', 'created_at')
    list_filter = ('post_type',)
    search_fields = ('content', 'author__username', 'thread__title')


@admin.register(ForumVote)
class ForumVoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'vote_type', 'created_at')


@admin.register(ForumBookmark)
class ForumBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'thread', 'created_at')


@admin.register(ForumReport)
class ForumReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'post', 'reason', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved')
    actions = ['mark_resolved']

    @admin.action(description="Mark selected reports as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)
