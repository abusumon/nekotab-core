import logging
from django.db.models import Avg, Count, Q, F, Sum, StdDev, Max
from .models import (
    DebatePassport, TournamentParticipation, RoundPerformance,
    JudgeBallot, Partnership, UserStats,
)

logger = logging.getLogger(__name__)


def recompute_user_stats(passport: DebatePassport):
    """Recompute all cached analytics for a user's debate passport."""

    stats, created = UserStats.objects.get_or_create(passport=passport)
    participations = passport.participations.all()

    # ---- Tournament-level stats ----
    stats.total_tournaments = participations.count()
    speaker_participations = participations.filter(role='speaker')
    if speaker_participations.exists():
        stats.break_rate = round(
            speaker_participations.filter(broke=True).count() / speaker_participations.count() * 100, 1
        )

    # ---- Round-level performance stats ----
    all_rounds = RoundPerformance.objects.filter(participation__passport=passport)
    stats.total_rounds = all_rounds.count()

    score_agg = all_rounds.filter(speaker_score__isnull=False).aggregate(
        avg_score=Avg('speaker_score'),
        max_score=Max('speaker_score'),
    )

    if score_agg.get('avg_score'):
        stats.average_speaker_score = round(score_agg['avg_score'], 2)
    if score_agg.get('max_score'):
        stats.highest_speaker_score = score_agg['max_score']

    # ---- Win rates ----
    win_results = ['win', '1st']
    total_scored = all_rounds.exclude(result='').count()
    if total_scored > 0:
        wins = all_rounds.filter(result__in=win_results).count()
        stats.overall_win_rate = round(wins / total_scored * 100, 1)

    gov_sides = ['gov', 'og', 'cg']
    opp_sides = ['opp', 'oo', 'co']

    gov_rounds = all_rounds.filter(side__in=gov_sides)
    opp_rounds = all_rounds.filter(side__in=opp_sides)
    if gov_rounds.exists():
        stats.gov_win_rate = round(
            gov_rounds.filter(result__in=win_results).count() / gov_rounds.count() * 100, 1
        )
    if opp_rounds.exists():
        stats.opp_win_rate = round(
            opp_rounds.filter(result__in=win_results).count() / opp_rounds.count() * 100, 1
        )

    # ---- Format distribution ----
    stats.format_distribution = dict(
        participations.values_list('tournament_format').annotate(c=Count('id')).values_list('tournament_format', 'c')
    )

    # ---- Judge analytics ----
    judge_parts = participations.filter(role='judge')
    all_ballots = JudgeBallot.objects.filter(participation__passport=passport)
    stats.judge_total_rounds = all_ballots.count()

    if all_ballots.exists():
        stats.judge_chair_rate = round(
            all_ballots.filter(was_chair=True).count() / all_ballots.count() * 100, 1
        )
        stats.judge_majority_agreement = round(
            all_ballots.filter(agreed_with_majority=True).count() / all_ballots.count() * 100, 1
        )

        # Average score given and variance
        all_scores = []
        for ballot in all_ballots:
            if ballot.scores_given:
                all_scores.extend(
                    [v for v in ballot.scores_given.values() if isinstance(v, (int, float))]
                )
        if all_scores:
            stats.judge_avg_score_given = round(sum(all_scores) / len(all_scores), 2)
            mean = stats.judge_avg_score_given
            variance = sum((s - mean) ** 2 for s in all_scores) / len(all_scores)
            stats.judge_score_variance = round(variance, 2)

    # ---- Performance trend ----
    years = participations.values_list('year', flat=True).distinct().order_by('year')
    trend = []
    for year in years:
        year_rounds = all_rounds.filter(participation__year=year)
        year_agg = year_rounds.filter(speaker_score__isnull=False).aggregate(avg=Avg('speaker_score'))
        year_wins = year_rounds.filter(result__in=win_results).count()
        year_total = year_rounds.count()
        trend.append({
            'year': year,
            'avg_score': round(year_agg['avg'] or 0, 2),
            'win_rate': round(year_wins / year_total * 100, 1) if year_total > 0 else 0,
            'tournaments': participations.filter(year=year).count(),
        })
    stats.performance_trend = trend

    stats.save()
    return stats


def compute_partnerships(passport: DebatePassport):
    """Compute partnership analytics from tournament participations."""
    participations = passport.participations.filter(role='speaker')
    partner_data = {}

    for p in participations:
        if not p.partner_names:
            continue

        for partner_name in p.partner_names:
            if partner_name not in partner_data:
                partner_data[partner_name] = {
                    'tournaments': 0,
                    'rounds': 0,
                    'wins': 0,
                    'total_score': 0,
                }
            partner_data[partner_name]['tournaments'] += 1

            rounds = p.round_performances.all()
            partner_data[partner_name]['rounds'] += rounds.count()
            partner_data[partner_name]['wins'] += rounds.filter(result__in=['win', '1st']).count()
            score_sum = rounds.filter(speaker_score__isnull=False).aggregate(s=Sum('speaker_score'))
            partner_data[partner_name]['total_score'] += score_sum['s'] or 0

    # Update or create partnerships
    for partner_name, data in partner_data.items():
        # Try to find partner's passport
        partner_passport = DebatePassport.objects.filter(display_name__iexact=partner_name).first()

        Partnership.objects.update_or_create(
            passport=passport,
            partner_name=partner_name,
            defaults={
                'partner_passport': partner_passport,
                'tournaments_together': data['tournaments'],
                'rounds_together': data['rounds'],
                'wins_together': data['wins'],
                'total_speaker_score': data['total_score'],
            },
        )
