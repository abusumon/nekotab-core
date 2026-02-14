from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# Forum Tags
# =============================================================================

class ForumTag(models.Model):
    """Tags for categorizing forum posts (e.g., 'Strategy', 'Theory')."""
    name = models.CharField(max_length=50, unique=True, verbose_name=_("name"))
    slug = models.SlugField(max_length=60, unique=True, verbose_name=_("slug"))
    color = models.CharField(max_length=7, default="#663da0", verbose_name=_("color hex"),
        help_text=_("Hex color for tag badge"))
    description = models.CharField(max_length=200, blank=True, verbose_name=_("description"))

    class Meta:
        verbose_name = _("forum tag")
        verbose_name_plural = _("forum tags")
        ordering = ['name']

    def __str__(self):
        return self.name


# =============================================================================
# User Debate Roles / Badges
# =============================================================================

class UserBadge(models.Model):
    """Verified role badges for forum credibility."""

    class BadgeType(models.TextChoices):
        VERIFIED_CA = 'verified_ca', _("Verified CA")
        CHIEF_ADJUDICATOR = 'chief_adj', _("Chief Adjudicator")
        NATIONAL_TEAM = 'national_team', _("National Team")
        WORLDS_BREAKER = 'worlds_breaker', _("Worlds Breaker")
        JUDGE_PANELIST = 'judge_panelist', _("Judge Panelist")
        TOURNAMENT_WINNER = 'tournament_winner', _("Tournament Winner")
        EXPERIENCED_DEBATER = 'experienced', _("Experienced Debater")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_badges', verbose_name=_("user"))
    badge_type = models.CharField(max_length=30, choices=BadgeType.choices, verbose_name=_("badge type"))
    verified = models.BooleanField(default=False, verbose_name=_("verified"))
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='badges_verified', verbose_name=_("verified by"))
    evidence = models.TextField(blank=True, verbose_name=_("evidence"),
        help_text=_("Link or description proving this credential"))
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("awarded at"))

    class Meta:
        verbose_name = _("user badge")
        verbose_name_plural = _("user badges")
        unique_together = ('user', 'badge_type')

    def __str__(self):
        return f"{self.user} — {self.get_badge_type_display()}"


# =============================================================================
# Forum Threads
# =============================================================================

class ForumThread(models.Model):
    """A structured discussion thread in the debate forum."""

    class DebateFormat(models.TextChoices):
        BP = 'bp', _("British Parliamentary")
        WSDC = 'wsdc', _("World Schools")
        AP = 'ap', _("Australs / Asian Parliamentary")
        PUBLIC_FORUM = 'pf', _("Public Forum")
        LINCOLN_DOUGLAS = 'ld', _("Lincoln-Douglas")
        POLICY = 'policy', _("Policy")
        CP = 'cp', _("Canadian Parliamentary")
        OTHER = 'other', _("Other")

    class TopicCategory(models.TextChoices):
        THEORY = 'theory', _("Theory")
        STRATEGY = 'strategy', _("Strategy")
        MOTIONS = 'motions', _("Motions")
        JUDGE_ISSUES = 'judge_issues', _("Judge Issues")
        META = 'meta', _("Meta")
        CASE_STUDY = 'case_study', _("Case Study")
        TRAINING = 'training', _("Training")

    class SkillLevel(models.TextChoices):
        NOVICE = 'novice', _("Novice")
        INTERMEDIATE = 'intermediate', _("Intermediate")
        ADVANCED = 'advanced', _("Advanced")
        ALL_LEVELS = 'all', _("All Levels")

    title = models.CharField(max_length=300, verbose_name=_("title"))
    slug = models.SlugField(max_length=320, unique=True, verbose_name=_("slug"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_threads', verbose_name=_("author"))

    # Structured categorization
    debate_format = models.CharField(max_length=20, choices=DebateFormat.choices,
        default=DebateFormat.BP, verbose_name=_("debate format"))
    topic_category = models.CharField(max_length=20, choices=TopicCategory.choices,
        default=TopicCategory.STRATEGY, verbose_name=_("topic category"))
    skill_level = models.CharField(max_length=20, choices=SkillLevel.choices,
        default=SkillLevel.ALL_LEVELS, verbose_name=_("skill level"))
    region = models.CharField(max_length=100, blank=True, verbose_name=_("region"),
        help_text=_("Geographic region relevance (optional)"))

    tags = models.ManyToManyField(ForumTag, blank=True, related_name='threads', verbose_name=_("tags"))

    # Motion link (auto-created threads for motions)
    linked_motion = models.ForeignKey('motionbank.MotionEntry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='forum_threads', verbose_name=_("linked motion"))

    # Metadata
    is_pinned = models.BooleanField(default=False, verbose_name=_("pinned"))
    is_locked = models.BooleanField(default=False, verbose_name=_("locked"))
    view_count = models.PositiveIntegerField(default=0, verbose_name=_("view count"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("forum thread")
        verbose_name_plural = _("forum threads")
        ordering = ['-is_pinned', '-updated_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['debate_format', 'topic_category']),
            models.Index(fields=['skill_level']),
        ]

    def __str__(self):
        return self.title

    @property
    def reply_count(self):
        return self.posts.count()

    @property
    def last_activity(self):
        last_post = self.posts.order_by('-created_at').first()
        return last_post.created_at if last_post else self.created_at


# =============================================================================
# Forum Posts (Argument Tree)
# =============================================================================

class ForumPost(models.Model):
    """A post in a forum thread, with structured reply types for argument trees."""

    class PostType(models.TextChoices):
        OPENING = 'opening', _("Opening Post")
        COUNTERARGUMENT = 'counter', _("Counterargument")
        SUPPORT = 'support', _("Support")
        CLARIFICATION = 'clarification', _("Clarification")
        EXAMPLE = 'example', _("Example")
        REBUTTAL = 'rebuttal', _("Rebuttal")
        EXTENSION = 'extension', _("Extension")
        FRAMEWORK = 'framework', _("Framework")
        WEIGHING = 'weighing', _("Weighing")

    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE,
        related_name='posts', verbose_name=_("thread"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_posts', verbose_name=_("author"))
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='children', verbose_name=_("parent post"),
        help_text=_("The post this is replying to (for argument tree structure)"))

    post_type = models.CharField(max_length=20, choices=PostType.choices,
        default=PostType.OPENING, verbose_name=_("post type"))
    content = models.TextField(verbose_name=_("content"))

    # Metadata
    is_edited = models.BooleanField(default=False, verbose_name=_("edited"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("forum post")
        verbose_name_plural = _("forum posts")
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.get_post_type_display()} by {self.author} in {self.thread}"

    @property
    def depth(self):
        """Calculate nesting depth for argument tree display."""
        depth = 0
        current = self
        while current.parent is not None:
            depth += 1
            current = current.parent
        return depth

    @property
    def vote_score(self):
        upvotes = self.votes.filter(vote_type=ForumVote.VoteType.UPVOTE).count()
        downvotes = self.votes.filter(vote_type=ForumVote.VoteType.DOWNVOTE).count()
        return upvotes - downvotes


# =============================================================================
# Forum Votes
# =============================================================================

class ForumVote(models.Model):
    """Votes on forum posts."""

    class VoteType(models.TextChoices):
        UPVOTE = 'up', _("Upvote")
        DOWNVOTE = 'down', _("Downvote")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_votes', verbose_name=_("user"))
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE,
        related_name='votes', verbose_name=_("post"))
    vote_type = models.CharField(max_length=5, choices=VoteType.choices, verbose_name=_("vote type"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("forum vote")
        verbose_name_plural = _("forum votes")
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user} {self.get_vote_type_display()} on {self.post}"


# =============================================================================
# Forum Bookmarks
# =============================================================================

class ForumBookmark(models.Model):
    """Bookmarked threads for users."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_bookmarks', verbose_name=_("user"))
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE,
        related_name='bookmarks', verbose_name=_("thread"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("forum bookmark")
        verbose_name_plural = _("forum bookmarks")
        unique_together = ('user', 'thread')

    def __str__(self):
        return f"{self.user} bookmarked {self.thread}"


# =============================================================================
# Forum Reports
# =============================================================================

class ForumReport(models.Model):
    """Reports on forum posts for moderation."""

    class ReportReason(models.TextChoices):
        SPAM = 'spam', _("Spam")
        HARASSMENT = 'harassment', _("Harassment")
        OFF_TOPIC = 'off_topic', _("Off-topic")
        MISINFORMATION = 'misinfo', _("Misinformation")
        OTHER = 'other', _("Other")

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_reports', verbose_name=_("reporter"))
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE,
        related_name='reports', verbose_name=_("post"))
    reason = models.CharField(max_length=20, choices=ReportReason.choices, verbose_name=_("reason"))
    details = models.TextField(blank=True, verbose_name=_("details"))
    resolved = models.BooleanField(default=False, verbose_name=_("resolved"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("forum report")
        verbose_name_plural = _("forum reports")
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter} on {self.post}"
