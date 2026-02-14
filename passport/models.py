from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# Debate Passport Profile
# =============================================================================

class DebatePassport(models.Model):
    """The main debate career profile — public-facing passport."""

    class ExperienceLevel(models.TextChoices):
        BEGINNER = 'beginner', _("Beginner (0-1 years)")
        INTERMEDIATE = 'intermediate', _("Intermediate (1-3 years)")
        ADVANCED = 'advanced', _("Advanced (3-5 years)")
        EXPERT = 'expert', _("Expert (5+ years)")
        PROFESSIONAL = 'professional', _("Professional / Coach")

    class PrimaryFormat(models.TextChoices):
        BP = 'bp', _("British Parliamentary")
        WSDC = 'wsdc', _("World Schools")
        AP = 'ap', _("Australs / Asian Parliamentary")
        PUBLIC_FORUM = 'pf', _("Public Forum")
        LINCOLN_DOUGLAS = 'ld', _("Lincoln-Douglas")
        POLICY = 'policy', _("Policy")
        CP = 'cp', _("Canadian Parliamentary")
        MULTIPLE = 'multi', _("Multiple Formats")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='debate_passport', verbose_name=_("user"))

    # Profile info
    display_name = models.CharField(max_length=100, verbose_name=_("display name"))
    bio = models.TextField(max_length=500, blank=True, verbose_name=_("bio"))
    country = models.CharField(max_length=100, blank=True, verbose_name=_("country"))
    country_code = models.CharField(max_length=3, blank=True, verbose_name=_("country code"),
        help_text=_("ISO 3166-1 alpha-2 country code for flag"))
    institution = models.CharField(max_length=200, blank=True, verbose_name=_("institution"))
    primary_format = models.CharField(max_length=20, choices=PrimaryFormat.choices,
        default=PrimaryFormat.BP, verbose_name=_("primary format"))
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices,
        default=ExperienceLevel.BEGINNER, verbose_name=_("experience level"))

    # Roles
    is_speaker = models.BooleanField(default=True, verbose_name=_("speaker"))
    is_judge = models.BooleanField(default=False, verbose_name=_("judge / adjudicator"))
    is_ca = models.BooleanField(default=False, verbose_name=_("chief adjudicator"))
    is_coach = models.BooleanField(default=False, verbose_name=_("coach / trainer"))

    # Privacy
    is_public = models.BooleanField(default=True, verbose_name=_("public profile"))
    show_scores = models.BooleanField(default=True, verbose_name=_("show scores"))
    show_analytics = models.BooleanField(default=True, verbose_name=_("show analytics"))

    # Avatar / branding
    avatar_url = models.URLField(blank=True, verbose_name=_("avatar URL"))
    timezone = models.CharField(max_length=50, default='UTC', verbose_name=_("timezone"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("debate passport")
        verbose_name_plural = _("debate passports")

    def __str__(self):
        return f"{self.display_name} — {self.get_primary_format_display()}"


# =============================================================================
# Tournament Participation
# =============================================================================

class TournamentParticipation(models.Model):
    """Record of participating in a tournament."""

    class Role(models.TextChoices):
        SPEAKER = 'speaker', _("Speaker")
        JUDGE = 'judge', _("Judge / Adjudicator")
        CA = 'ca', _("Chief Adjudicator")
        DCA = 'dca', _("Deputy Chief Adjudicator")
        TAB_DIRECTOR = 'tab_dir', _("Tab Director")
        COACH = 'coach', _("Coach")

    passport = models.ForeignKey(DebatePassport, on_delete=models.CASCADE,
        related_name='participations', verbose_name=_("passport"))

    # Tournament info
    tournament_name = models.CharField(max_length=200, verbose_name=_("tournament name"))
    tournament_format = models.CharField(max_length=20, choices=DebatePassport.PrimaryFormat.choices,
        verbose_name=_("format"))
    year = models.PositiveIntegerField(verbose_name=_("year"))
    location = models.CharField(max_length=200, blank=True, verbose_name=_("location"))
    num_rounds = models.PositiveIntegerField(default=0, verbose_name=_("number of rounds"))

    # Role & result
    role = models.CharField(max_length=10, choices=Role.choices,
        default=Role.SPEAKER, verbose_name=_("role"))
    team_name = models.CharField(max_length=200, blank=True, verbose_name=_("team name"))
    partner_names = models.JSONField(default=list, blank=True, verbose_name=_("partner names"))
    broke = models.BooleanField(default=False, verbose_name=_("broke (reached elimination rounds)"))
    break_category = models.CharField(max_length=100, blank=True, verbose_name=_("break category"),
        help_text=_("e.g., 'Open Break', 'ESL Break', 'EFL Break'"))
    final_rank = models.CharField(max_length=50, blank=True, verbose_name=_("final rank"),
        help_text=_("e.g., 'Grand Finalist', 'Semi-finalist', '15th'"))

    # Link to internal Tabbycat tournament
    internal_tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='passport_participations', verbose_name=_("linked tournament"))

    # Metadata
    verified = models.BooleanField(default=False, verbose_name=_("verified"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("tournament participation")
        verbose_name_plural = _("tournament participations")
        ordering = ['-year', '-created_at']

    def __str__(self):
        return f"{self.passport.display_name} @ {self.tournament_name} ({self.year})"


# =============================================================================
# Round Performance
# =============================================================================

class RoundPerformance(models.Model):
    """Per-round performance data for speaker analytics."""

    class Side(models.TextChoices):
        GOV = 'gov', _("Government / Proposition")
        OPP = 'opp', _("Opposition")
        OG = 'og', _("Opening Government")
        OO = 'oo', _("Opening Opposition")
        CG = 'cg', _("Closing Government")
        CO = 'co', _("Closing Opposition")

    class Position(models.TextChoices):
        PM = 'pm', _("Prime Minister / 1st Prop")
        DPM = 'dpm', _("Deputy PM / 2nd Prop")
        LO = 'lo', _("Leader of Opposition / 1st Opp")
        DLO = 'dlo', _("Deputy LO / 2nd Opp")
        MG = 'mg', _("Member of Government / 3rd Prop")
        GW = 'gw', _("Government Whip / 4th Prop")
        MO = 'mo', _("Member of Opposition / 3rd Opp")
        OW = 'ow', _("Opposition Whip / 4th Opp")
        FIRST = 'first', _("1st Speaker")
        SECOND = 'second', _("2nd Speaker")
        THIRD = 'third', _("3rd Speaker")
        REPLY = 'reply', _("Reply Speaker")

    class RoundResult(models.TextChoices):
        WIN = 'win', _("Win")
        LOSS = 'loss', _("Loss")
        FIRST_PLACE = '1st', _("1st Place (BP)")
        SECOND_PLACE = '2nd', _("2nd Place (BP)")
        THIRD_PLACE = '3rd', _("3rd Place (BP)")
        FOURTH_PLACE = '4th', _("4th Place (BP)")

    participation = models.ForeignKey(TournamentParticipation, on_delete=models.CASCADE,
        related_name='round_performances', verbose_name=_("participation"))
    round_number = models.PositiveIntegerField(verbose_name=_("round number"))
    round_name = models.CharField(max_length=100, blank=True, verbose_name=_("round name"),
        help_text=_("e.g., 'Round 1', 'Quarterfinals'"))

    side = models.CharField(max_length=5, choices=Side.choices, verbose_name=_("side"))
    position = models.CharField(max_length=10, choices=Position.choices,
        blank=True, verbose_name=_("speaking position"))
    result = models.CharField(max_length=5, choices=RoundResult.choices, verbose_name=_("result"))

    # Scores
    speaker_score = models.FloatField(null=True, blank=True, verbose_name=_("speaker score"))
    average_score_in_round = models.FloatField(null=True, blank=True,
        verbose_name=_("average speaker score in round"))

    # Motion
    motion_text = models.TextField(blank=True, verbose_name=_("motion"))

    class Meta:
        verbose_name = _("round performance")
        verbose_name_plural = _("round performances")
        ordering = ['participation', 'round_number']
        unique_together = ('participation', 'round_number')

    def __str__(self):
        return f"Round {self.round_number}: {self.get_result_display()} ({self.speaker_score})"


# =============================================================================
# Judge Ballot (for judge analytics)
# =============================================================================

class JudgeBallot(models.Model):
    """Records a judging ballot for judge analytics."""

    participation = models.ForeignKey(TournamentParticipation, on_delete=models.CASCADE,
        related_name='judge_ballots', verbose_name=_("participation"))
    round_number = models.PositiveIntegerField(verbose_name=_("round number"))
    round_name = models.CharField(max_length=100, blank=True, verbose_name=_("round name"))

    # Judge panel info
    was_chair = models.BooleanField(default=False, verbose_name=_("was chair"))
    panel_size = models.PositiveIntegerField(default=1, verbose_name=_("panel size"))
    agreed_with_majority = models.BooleanField(default=True, verbose_name=_("agreed with majority"))

    # Scores given (JSON: {team_name: score, ...} or {speaker_name: score, ...})
    scores_given = models.JSONField(default=dict, blank=True, verbose_name=_("scores given"))

    # Motion
    motion_text = models.TextField(blank=True, verbose_name=_("motion"))

    class Meta:
        verbose_name = _("judge ballot")
        verbose_name_plural = _("judge ballots")
        ordering = ['participation', 'round_number']

    def __str__(self):
        chair_str = " (Chair)" if self.was_chair else ""
        return f"Ballot R{self.round_number}{chair_str}"


# =============================================================================
# Partnership Analytics
# =============================================================================

class Partnership(models.Model):
    """Track debating partnerships and synergy."""

    passport = models.ForeignKey(DebatePassport, on_delete=models.CASCADE,
        related_name='partnerships', verbose_name=_("passport"))
    partner_name = models.CharField(max_length=200, verbose_name=_("partner name"))
    partner_passport = models.ForeignKey(DebatePassport, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='partnerships_as_partner', verbose_name=_("partner passport"))

    tournaments_together = models.PositiveIntegerField(default=0, verbose_name=_("tournaments together"))
    rounds_together = models.PositiveIntegerField(default=0, verbose_name=_("rounds together"))
    wins_together = models.PositiveIntegerField(default=0, verbose_name=_("wins together"))
    total_speaker_score = models.FloatField(default=0, verbose_name=_("total combined speaker score"))

    class Meta:
        verbose_name = _("partnership")
        verbose_name_plural = _("partnerships")
        ordering = ['-tournaments_together']

    def __str__(self):
        return f"{self.passport.display_name} & {self.partner_name}"

    @property
    def win_rate(self):
        if self.rounds_together == 0:
            return 0
        return round(self.wins_together / self.rounds_together * 100, 1)

    @property
    def avg_speaker_score(self):
        if self.rounds_together == 0:
            return 0
        return round(self.total_speaker_score / self.rounds_together, 1)


# =============================================================================
# Cached User Stats (Precomputed Analytics)
# =============================================================================

class UserStats(models.Model):
    """Precomputed analytics for fast dashboard rendering."""

    passport = models.OneToOneField(DebatePassport, on_delete=models.CASCADE,
        related_name='cached_stats', verbose_name=_("passport"))

    # Performance summary
    total_tournaments = models.PositiveIntegerField(default=0, verbose_name=_("total tournaments"))
    total_rounds = models.PositiveIntegerField(default=0, verbose_name=_("total rounds"))
    break_rate = models.FloatField(default=0, verbose_name=_("break rate (%)"))
    average_speaker_score = models.FloatField(default=0, verbose_name=_("average speaker score"))
    highest_speaker_score = models.FloatField(default=0, verbose_name=_("highest speaker score"))

    # Win rates
    overall_win_rate = models.FloatField(default=0, verbose_name=_("overall win rate (%)"))
    gov_win_rate = models.FloatField(default=0, verbose_name=_("gov/prop win rate (%)"))
    opp_win_rate = models.FloatField(default=0, verbose_name=_("opp win rate (%)"))

    # Format distribution (JSON: {format_code: count, ...})
    format_distribution = models.JSONField(default=dict, blank=True, verbose_name=_("format distribution"))

    # Skill Radar (0-100 scores)
    skill_framing = models.FloatField(default=50, verbose_name=_("framing skill"))
    skill_clash = models.FloatField(default=50, verbose_name=_("clash skill"))
    skill_extension = models.FloatField(default=50, verbose_name=_("extension quality"))
    skill_weighing = models.FloatField(default=50, verbose_name=_("weighing skill"))
    skill_rebuttal = models.FloatField(default=50, verbose_name=_("rebuttal skill"))
    skill_strategy = models.FloatField(default=50, verbose_name=_("strategy skill"))
    skill_delivery = models.FloatField(default=50, verbose_name=_("delivery skill"))

    # Judge stats
    judge_total_rounds = models.PositiveIntegerField(default=0, verbose_name=_("total judging rounds"))
    judge_chair_rate = models.FloatField(default=0, verbose_name=_("chair rate (%)"))
    judge_avg_score_given = models.FloatField(default=0, verbose_name=_("average score given"))
    judge_score_variance = models.FloatField(default=0, verbose_name=_("score variance"))
    judge_majority_agreement = models.FloatField(default=0, verbose_name=_("majority agreement rate (%)"))

    # Performance trend (JSON: [{year, avg_score, win_rate, tournaments}, ...])
    performance_trend = models.JSONField(default=list, blank=True, verbose_name=_("performance trend"))

    last_computed = models.DateTimeField(auto_now=True, verbose_name=_("last computed"))

    class Meta:
        verbose_name = _("user stats")
        verbose_name_plural = _("user stats")

    def __str__(self):
        return f"Stats for {self.passport.display_name}"
