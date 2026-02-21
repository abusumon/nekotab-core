from django.db import models
from django.utils.text import slugify
from django.urls import reverse


class ArticleCategory(models.Model):
    """Categories for the /learn content hub."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji icon")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Article Categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('content:learn-hub') + f'?category={self.slug}'

    @property
    def published_count(self):
        return self.articles.filter(status=Article.Status.PUBLISHED).count()


class Article(models.Model):
    """Content articles for the /learn section.
    Designed for stub creation now, full articles later."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.TextField(
        max_length=500,
        help_text="Short description shown in listings and meta tags (max 500 chars)."
    )
    body = models.TextField(
        blank=True,
        help_text="Article body (HTML allowed, will be sanitized on render)."
    )
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='articles'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    reading_time_minutes = models.PositiveSmallIntegerField(
        default=1,
        help_text="Estimated reading time in minutes."
    )
    # SEO fields
    meta_title = models.CharField(max_length=70, blank=True, help_text="Override title tag")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Override meta description")

    # Internal linking: map articles to debate format slugs for cross-linking
    related_format_slugs = models.JSONField(
        default=list, blank=True,
        help_text='List of debate format identifiers (e.g. ["bp","australs"]) for cross-linking from tournament pages.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='content_art_status_fc7162_idx'),
            models.Index(fields=['slug'], name='content_art_slug_d82f31_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:article-detail', kwargs={'slug': self.slug})

    @property
    def is_indexable(self):
        """Only published articles with meaningful content should be indexed."""
        return (
            self.status == self.Status.PUBLISHED
            and len(self.body) > 100
        )

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        return self.meta_description or self.summary[:160]


class TournamentContentBlock(models.Model):
    """Editable contextual content for public tournament pages.
    Stored as sanitized text, rendered on /t/:slug landing."""
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='content_block'
    )
    about_text = models.TextField(
        blank=True,
        help_text="About this tournament (shown on public page, max 2000 chars)."
    )
    host_organization = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    format_description = models.CharField(
        max_length=100, blank=True,
        help_text="e.g. British Parliamentary, Australs 3v3"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status_label = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. Completed, In Progress, Upcoming"
    )
    # Override SEO for this tournament's public page
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tournament Content Block'

    def __str__(self):
        return f"Content block for {self.tournament}"

    @property
    def has_meaningful_content(self):
        """Determines if this block adds enough value for indexing."""
        return bool(self.about_text and len(self.about_text) > 50)
