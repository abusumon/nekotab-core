from django.contrib import admin
from .models import Article, ArticleCategory, TournamentContentBlock


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'order', 'published_count')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'reading_time_minutes', 'updated_at', 'is_indexable')
    list_filter = ('status', 'category')
    search_fields = ('title', 'summary', 'body')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'is_indexable')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'status', 'summary', 'body', 'reading_time_minutes')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'related_format_slugs'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_indexable'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TournamentContentBlock)
class TournamentContentBlockAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'host_organization', 'format_description', 'status_label', 'updated_at')
    search_fields = ('tournament__name', 'host_organization')
    raw_id_fields = ('tournament',)
    fieldsets = (
        (None, {
            'fields': ('tournament', 'about_text', 'host_organization', 'location',
                        'format_description', 'start_date', 'end_date', 'status_label')
        }),
        ('SEO Override', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
