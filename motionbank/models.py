import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# Motion Entry (Global Motion Bank)
# =============================================================================

class MotionEntry(models.Model):
    """A motion in the global motion bank — independent of tournament instances."""

    class MotionFormat(models.TextChoices):
        BP = 'bp', _("British Parliamentary")
        WSDC = 'wsdc', _("World Schools")
        AP = 'ap', _("Australs / Asian Parliamentary")
        PUBLIC_FORUM = 'pf', _("Public Forum")
        LINCOLN_DOUGLAS = 'ld', _("Lincoln-Douglas")
        POLICY = 'policy', _("Policy")
        CP = 'cp', _("Canadian Parliamentary")
        OTHER = 'other', _("Other")

    class MotionType(models.TextChoices):
        POLICY = 'policy', _("Policy")
        VALUE = 'value', _("Value")
        ACTOR = 'actor', _("Actor-Specific")
        THB = 'thb', _("This House Believes")
        THW = 'thw', _("This House Would")
        THBT = 'thbt', _("This House Believes That")
        THR = 'thr', _("This House Regrets")
        THS = 'ths', _("This House Supports")
        FACTUAL = 'factual', _("Factual")
        OTHER = 'other', _("Other")

    class Difficulty(models.IntegerChoices):
        BEGINNER = 1, _("Beginner")
        EASY = 2, _("Easy")
        MODERATE = 3, _("Moderate")
        HARD = 4, _("Hard")
        EXPERT = 5, _("Expert")

    class PrepType(models.TextChoices):
        PREPARED = 'prepared', _("Prepared")
        IMPROMPTU = 'impromptu', _("Impromptu")

    # Core fields
    text = models.TextField(verbose_name=_("motion text"))
    slug = models.SlugField(max_length=350, unique=True, verbose_name=_("slug"))
    info_slide = models.TextField(blank=True, verbose_name=_("info slide"))

    # Classification
    format = models.CharField(max_length=20, choices=MotionFormat.choices,
        default=MotionFormat.BP, verbose_name=_("debate format"))
    motion_type = models.CharField(max_length=20, choices=MotionType.choices,
        default=MotionType.THW, verbose_name=_("motion type"))
    difficulty = models.IntegerField(choices=Difficulty.choices,
        default=Difficulty.MODERATE, verbose_name=_("difficulty"))
    prep_type = models.CharField(max_length=20, choices=PrepType.choices,
        default=PrepType.IMPROMPTU, verbose_name=_("preparation type"))

    # Tournament context
    tournament_name = models.CharField(max_length=200, blank=True, verbose_name=_("tournament name"))
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("year"))
    region = models.CharField(max_length=100, blank=True, verbose_name=_("region"))
    round_info = models.CharField(max_length=100, blank=True, verbose_name=_("round info"),
        help_text=_("e.g., 'Grand Final', 'Round 3', 'Quarterfinals'"))

    # Theme / Tags
    theme_tags = models.JSONField(default=list, blank=True, verbose_name=_("theme tags"),
        help_text=_("e.g., ['economics', 'environment', 'human rights']"))
    source = models.CharField(max_length=300, blank=True, verbose_name=_("source"),
        help_text=_("Where this motion was collected from"))

    # Link to internal tournament motion (if imported from Tabbycat)
    internal_motion = models.ForeignKey('motions.Motion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='motionbank_entry', verbose_name=_("linked internal motion"))

    # Metadata
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='submitted_motions', verbose_name=_("submitted by"))
    is_approved = models.BooleanField(default=False, verbose_name=_("approved"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("motion entry")
        verbose_name_plural = _("motion entries")
        ordering = ['-year', '-created_at']
        indexes = [
            models.Index(fields=['format', 'year']),
            models.Index(fields=['motion_type']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.text[:120]


# =============================================================================
# AI Motion Analysis (Motion Doctor)
# =============================================================================

class MotionAnalysis(models.Model):
    """AI-generated analysis for a motion — the Motion Doctor output."""

    motion = models.OneToOneField(MotionEntry, on_delete=models.CASCADE,
        related_name='analysis', verbose_name=_("motion"))

    # Structured AI analysis stored as JSON
    ai_analysis = models.JSONField(default=dict, verbose_name=_("AI analysis"),
        help_text=_("""JSON structure:
        {
            "hidden_assumptions": ["..."],
            "model_problems": ["..."],
            "clash_areas": ["..."],
            "framing_mistakes": ["..."],
            "gov_approach": { "structure": "...", "key_args": ["..."] },
            "opp_approach": { "structure": "...", "key_args": ["..."] },
            "definition_traps": ["..."],
            "burden_split": "...",
            "likely_extensions": { "OG": "...", "OO": "...", "CG": "...", "CO": "..." },
            "weighing_options": ["..."],
            "suggested_pois": ["..."],
            "difficulty_rationale": "..."
        }"""))

    # Analysis metadata
    model_used = models.CharField(max_length=100, blank=True, verbose_name=_("AI model used"))
    confidence_score = models.FloatField(null=True, blank=True, verbose_name=_("confidence score"))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_("last updated"))

    class Meta:
        verbose_name = _("motion analysis")
        verbose_name_plural = _("motion analyses")

    def __str__(self):
        return f"Analysis for: {self.motion.text[:80]}"


# =============================================================================
# Motion Stats (Community Data)
# =============================================================================

class MotionStats(models.Model):
    """Aggregate statistics for a motion in the bank."""

    motion = models.OneToOneField(MotionEntry, on_delete=models.CASCADE,
        related_name='stats', verbose_name=_("motion"))

    times_practiced = models.PositiveIntegerField(default=0, verbose_name=_("times practiced"))
    times_used_in_tournaments = models.PositiveIntegerField(default=0, verbose_name=_("times used"))
    forum_thread_count = models.PositiveIntegerField(default=0, verbose_name=_("forum threads"))
    average_rating = models.FloatField(default=0.0, verbose_name=_("average rating"))
    total_ratings = models.PositiveIntegerField(default=0, verbose_name=_("total ratings"))
    gov_win_rate = models.FloatField(null=True, blank=True, verbose_name=_("gov win rate"),
        help_text=_("Percentage of times gov/prop side won"))

    class Meta:
        verbose_name = _("motion stats")
        verbose_name_plural = _("motion stats")

    def __str__(self):
        return f"Stats for: {self.motion.text[:80]}"


# =============================================================================
# Motion Rating
# =============================================================================

class MotionRating(models.Model):
    """User rating for a motion."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='motion_ratings', verbose_name=_("user"))
    motion = models.ForeignKey(MotionEntry, on_delete=models.CASCADE,
        related_name='ratings', verbose_name=_("motion"))
    score = models.PositiveSmallIntegerField(verbose_name=_("score"),
        help_text=_("1-5 star rating"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("motion rating")
        verbose_name_plural = _("motion ratings")
        unique_together = ('user', 'motion')

    def __str__(self):
        return f"{self.user} rated {self.motion.text[:50]}: {self.score}/5"


# =============================================================================
# Community Case Outlines
# =============================================================================

class CaseOutline(models.Model):
    """Community-submitted case outlines for motions."""

    class Side(models.TextChoices):
        GOV = 'gov', _("Government / Proposition")
        OPP = 'opp', _("Opposition")
        OG = 'og', _("Opening Government")
        OO = 'oo', _("Opening Opposition")
        CG = 'cg', _("Closing Government")
        CO = 'co', _("Closing Opposition")

    motion = models.ForeignKey(MotionEntry, on_delete=models.CASCADE,
        related_name='case_outlines', verbose_name=_("motion"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='case_outlines', verbose_name=_("author"))
    side = models.CharField(max_length=5, choices=Side.choices, verbose_name=_("side"))
    title = models.CharField(max_length=200, verbose_name=_("title"))
    content = models.TextField(verbose_name=_("case outline content"),
        help_text=_("Structured case outline with arguments, examples, weighing"))
    upvotes = models.PositiveIntegerField(default=0, verbose_name=_("upvotes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("case outline")
        verbose_name_plural = _("case outlines")
        ordering = ['-upvotes', '-created_at']

    def __str__(self):
        return f"{self.get_side_display()}: {self.title}"


class CaseOutlineVote(models.Model):
    """Upvotes for case outlines."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='case_outline_votes', verbose_name=_("user"))
    case_outline = models.ForeignKey(CaseOutline, on_delete=models.CASCADE,
        related_name='votes', verbose_name=_("case outline"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("case outline vote")
        verbose_name_plural = _("case outline votes")
        unique_together = ('user', 'case_outline')


# =============================================================================
# Practice Sessions
# =============================================================================

class PracticeSession(models.Model):
    """Track when users practice a motion."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='practice_sessions', verbose_name=_("user"))
    motion = models.ForeignKey(MotionEntry, on_delete=models.CASCADE,
        related_name='practice_sessions', verbose_name=_("motion"))
    side_practiced = models.CharField(max_length=5, choices=CaseOutline.Side.choices,
        blank=True, verbose_name=_("side practiced"))
    notes = models.TextField(blank=True, verbose_name=_("notes"))
    duration_minutes = models.PositiveIntegerField(null=True, blank=True,
        verbose_name=_("duration (minutes)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("practice session")
        verbose_name_plural = _("practice sessions")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} practiced: {self.motion.text[:60]}"


# =============================================================================
# Motion Profile (Structured Classifier Output)
# =============================================================================

class MotionProfile(models.Model):
    """Structured classifier output for a motion — the 'brain' of Motion Doctor."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    motion = models.OneToOneField(MotionEntry, on_delete=models.CASCADE,
        related_name='profile', verbose_name=_("motion"))

    # Classification fields
    format = models.CharField(max_length=20, blank=True, verbose_name=_("debate format"))
    motion_type = models.CharField(max_length=50, blank=True, verbose_name=_("motion type"),
        help_text=_("policy / value / actor / regret / comparative / unclear"))
    domain_primary = models.CharField(max_length=100, blank=True, verbose_name=_("primary domain"),
        help_text=_("bioethics / ai / econ / war / identity / etc."))
    domain_secondary = models.JSONField(default=list, blank=True, verbose_name=_("secondary domains"))

    # Motion structure
    actor = models.CharField(max_length=200, blank=True, verbose_name=_("actor"),
        help_text=_("e.g., the_state, UN, parents"))
    action = models.CharField(max_length=200, blank=True, verbose_name=_("action"),
        help_text=_("e.g., ban, regulate, subsidize"))
    object_field = models.CharField(max_length=300, blank=True, verbose_name=_("object"),
        help_text=_("e.g., genetic engineering, social media"))

    # Scope
    scope = models.JSONField(default=dict, blank=True, verbose_name=_("scope"),
        help_text=_("geography, timeframe, subjects, exceptions"))

    # Flags & metadata
    requires_model = models.BooleanField(default=False, verbose_name=_("requires gov model"))
    ambiguity_flags = models.JSONField(default=list, blank=True, verbose_name=_("ambiguity flags"))
    keywords = models.JSONField(default=list, blank=True, verbose_name=_("extracted keywords"))
    constraints = models.JSONField(default=list, blank=True, verbose_name=_("constraints"))
    extracted_entities = models.JSONField(default=dict, blank=True, verbose_name=_("extracted entities"))
    confidence = models.FloatField(default=0.0, verbose_name=_("classifier confidence"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("motion profile")
        verbose_name_plural = _("motion profiles")

    def __str__(self):
        return f"Profile: {self.motion_type} / {self.domain_primary} (conf={self.confidence:.2f})"


# =============================================================================
# Archetype Library
# =============================================================================

class Archetype(models.Model):
    """A reusable debate archetype — the coaching knowledge base."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True, verbose_name=_("archetype name"),
        help_text=_("e.g., bioethics_restriction, prohibition_black_market"))
    description = models.TextField(blank=True, verbose_name=_("description"))

    # Classification
    domain_tags = models.JSONField(default=list, blank=True, verbose_name=_("domain tags"))
    trigger_features = models.JSONField(default=dict, blank=True, verbose_name=_("trigger features"),
        help_text=_("Keywords/patterns that activate this archetype"))

    # Coaching content
    canonical_clashes = models.JSONField(default=list, blank=True, verbose_name=_("canonical clash axes"))
    canonical_stakeholders = models.JSONField(default=list, blank=True, verbose_name=_("canonical stakeholders"))
    gov_playbook = models.JSONField(default=dict, blank=True, verbose_name=_("gov playbook"))
    opp_playbook = models.JSONField(default=dict, blank=True, verbose_name=_("opp playbook"))
    extension_templates = models.JSONField(default=dict, blank=True, verbose_name=_("extension templates"))
    definition_traps = models.JSONField(default=list, blank=True, verbose_name=_("definition traps"))
    weighing_tools = models.JSONField(default=list, blank=True, verbose_name=_("weighing tools"))
    red_flags = models.JSONField(default=list, blank=True, verbose_name=_("red flags"),
        help_text=_("Common mistakes or things to avoid"))

    # For retrieval
    embedding = models.JSONField(default=list, blank=True, verbose_name=_("embedding vector"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("archetype")
        verbose_name_plural = _("archetypes")
        ordering = ['name']

    def __str__(self):
        return self.name


class ArchetypeExample(models.Model):
    """Example motions linked to an archetype for retrieval."""

    archetype = models.ForeignKey(Archetype, on_delete=models.CASCADE,
        related_name='examples', verbose_name=_("archetype"))
    example_motion_text = models.TextField(verbose_name=_("example motion text"))
    notes = models.TextField(blank=True, verbose_name=_("notes"))
    embedding = models.JSONField(default=list, blank=True, verbose_name=_("embedding vector"))

    class Meta:
        verbose_name = _("archetype example")
        verbose_name_plural = _("archetype examples")

    def __str__(self):
        return f"{self.archetype.name}: {self.example_motion_text[:80]}"


# =============================================================================
# Motion Report (Full Doctor Output)
# =============================================================================

class MotionReport(models.Model):
    """The full Motion Doctor report — generated JSON output."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    motion = models.ForeignKey(MotionEntry, on_delete=models.CASCADE,
        related_name='reports', verbose_name=_("motion"), null=True, blank=True)
    motion_text = models.TextField(verbose_name=_("motion text"),
        help_text=_("Stored separately so reports work for ad-hoc motions too"))
    info_slide = models.TextField(blank=True, verbose_name=_("info slide"))
    format = models.CharField(max_length=20, blank=True, verbose_name=_("format"))

    # Full report JSON (the big schema from the plan)
    report_json = models.JSONField(default=dict, verbose_name=_("report JSON"))

    # Pipeline intermediaries (for debugging / re-runs)
    profile_json = models.JSONField(default=dict, blank=True, verbose_name=_("motion profile JSON"))
    plan_json = models.JSONField(default=dict, blank=True, verbose_name=_("planner outline JSON"))
    validation_log = models.JSONField(default=list, blank=True, verbose_name=_("validation log"))

    # Metadata
    model_version = models.CharField(max_length=100, blank=True, verbose_name=_("model version"))
    pipeline_duration_ms = models.PositiveIntegerField(null=True, blank=True,
        verbose_name=_("pipeline duration (ms)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("motion report")
        verbose_name_plural = _("motion reports")
        ordering = ['-created_at']

    def __str__(self):
        return f"Report for: {self.motion_text[:80]}"


# =============================================================================
# Report Feedback (Evaluation Loop)
# =============================================================================

class MotionReportFeedback(models.Model):
    """User feedback on a Motion Doctor report — drives evaluation."""

    report = models.ForeignKey(MotionReport, on_delete=models.CASCADE,
        related_name='feedback', verbose_name=_("report"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='report_feedback', verbose_name=_("user"))

    rating = models.PositiveSmallIntegerField(verbose_name=_("overall rating"),
        help_text=_("1–5 stars"))
    was_specific = models.BooleanField(default=False, verbose_name=_("was motion-specific"))
    was_fair = models.BooleanField(default=False, verbose_name=_("was fair / balanced"))
    was_helpful = models.BooleanField(default=False, verbose_name=_("was helpful"))
    generic_section = models.CharField(max_length=100, blank=True,
        verbose_name=_("which section felt generic"))
    free_text = models.TextField(blank=True, verbose_name=_("free text feedback"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("report feedback")
        verbose_name_plural = _("report feedback")
        unique_together = ('report', 'user')

    def __str__(self):
        return f"Feedback by {self.user} on report {self.report_id}"
