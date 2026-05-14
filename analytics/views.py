import csv
import io
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import connection
from django.db.models import Case, Count, DecimalField, F, Max, Q, Sum, Value, When
from django.db.models.functions import Coalesce, TruncDate, TruncHour, TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView, ListView, View

from tournaments.models import Tournament, Round
from results.models import BallotSubmission
from motionbank.models import MotionEntry
from participant_crm.models import ParticipantProfile
from participants.models import Speaker, Adjudicator
from donations.models import DonationTransaction
from .models import PageView, DailyStats, ActiveSession

User = get_user_model()
logger = logging.getLogger(__name__)


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only superusers can access the dashboard."""
    login_url = '/accounts/login/'
    raise_exception = False

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            # Authenticated but not superuser — redirect to home instead of 403
            return redirect('/')
        return super().handle_no_permission()


@method_decorator(cache_page(60), name='dispatch')
class DashboardView(SuperuserRequiredMixin, TemplateView):
    """Main analytics dashboard with overview stats."""
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = now.date()
        
        # Time ranges
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Real-time live visitors (exclude health-check paths)
        ActiveSession.cleanup_stale()
        live_sessions = ActiveSession.objects.exclude(current_path='/health/')
        context['live_visitors'] = live_sessions.count()
        context['active_sessions'] = live_sessions[:10]
        
        # === TODAY'S STATS ===
        today_views = PageView.objects.filter(timestamp__date=today)
        context['today_views'] = today_views.count()
        context['today_unique'] = today_views.values('session_key').distinct().count()
        context['today_signups'] = User.objects.filter(date_joined__date=today).count()
        
        # === TRAFFIC STATS ===
        context['views_24h'] = PageView.objects.filter(timestamp__gte=last_24h).count()
        context['views_7d'] = PageView.objects.filter(timestamp__gte=last_7d).count()
        context['views_30d'] = PageView.objects.filter(timestamp__gte=last_30d).count()
        
        # Unique visitors
        context['unique_24h'] = PageView.objects.filter(
            timestamp__gte=last_24h
        ).values('session_key').distinct().count()
        context['unique_7d'] = PageView.objects.filter(
            timestamp__gte=last_7d
        ).values('session_key').distinct().count()
        
        # === USER STATS ===
        context['total_users'] = User.objects.count()
        context['users_with_email'] = User.objects.exclude(email='').exclude(email__isnull=True).count()
        context['superusers'] = User.objects.filter(is_superuser=True).count()
        context['staff_users'] = User.objects.filter(is_staff=True).count()
        
        # Recent signups
        context['recent_signups'] = User.objects.order_by('-date_joined')[:10]
        
        # Signups over time (last 30 days)
        signups_by_day = User.objects.filter(
            date_joined__gte=last_30d
        ).annotate(
            day=TruncDate('date_joined')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        context['signups_chart_data'] = json.dumps([
            {'date': str(s['day']), 'count': s['count']} for s in signups_by_day
        ])
        
        # === TOURNAMENT STATS ===
        context['total_tournaments'] = Tournament.objects.count()
        context['active_tournaments'] = Tournament.objects.filter(active=True).count()

        # === PARTICIPANT STATS (real counts — not email-gated CRM) ===
        context['total_speakers'] = Speaker.objects.count()
        context['total_adjudicators'] = Adjudicator.objects.count()

        # Recent tournaments with real participant counts
        context['recent_tournaments'] = Tournament.objects.select_related('owner').annotate(
            num_teams=Count('team', distinct=True),
            num_speakers=Count('team__speaker', distinct=True),
            num_adjudicators=Count('adjudicator', distinct=True),
        ).order_by('-id')[:10]

        # === DEBATE STATS ===
        total_rounds = Round.objects.count()
        context['total_rounds'] = total_rounds
        
        # Ballots
        context['total_ballots'] = BallotSubmission.objects.count()
        context['ballots_today'] = BallotSubmission.objects.filter(timestamp__date=today).count()
        context['ballots_7d'] = BallotSubmission.objects.filter(timestamp__gte=last_7d).count()
        
        # === TRAFFIC BY HOUR (last 24h) ===
        hourly_traffic = PageView.objects.filter(
            timestamp__gte=last_24h
        ).annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        context['hourly_chart_data'] = json.dumps([
            {'hour': h['hour'].strftime('%H:%M'), 'count': h['count']} for h in hourly_traffic
        ])
        
        # === TOP PAGES ===
        top_pages = PageView.objects.filter(
            timestamp__gte=last_7d
        ).values('path').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        context['top_pages'] = top_pages
        
        # === DEVICE BREAKDOWN ===
        devices = PageView.objects.filter(
            timestamp__gte=last_7d
        ).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        device_stats = {d['device_type']: d['count'] for d in devices}
        context['device_stats'] = device_stats
        context['device_total'] = sum(device_stats.values()) or 1  # avoid division by zero
        
        # === BROWSER BREAKDOWN ===
        browsers = PageView.objects.filter(
            timestamp__gte=last_7d
        ).values('browser').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        context['browser_stats'] = browsers
        
        # === COUNTRY BREAKDOWN ===
        countries = PageView.objects.filter(
            timestamp__gte=last_7d
        ).exclude(country='').values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        context['country_stats'] = countries
        
        # === REFERRERS ===
        referrers = PageView.objects.filter(
            timestamp__gte=last_7d
        ).exclude(referer='').values('referer').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        context['referrer_stats'] = referrers

        # === MOTION BANK STATS ===
        context['total_motions'] = MotionEntry.objects.count()
        context['motions_by_format'] = list(
            MotionEntry.objects.values('format').annotate(count=Count('id')).order_by('-count')[:6]
        )

        # === PARTICIPANT CRM STATS ===
        crm = ParticipantProfile.objects
        context['crm_total'] = crm.count()
        context['crm_debaters'] = crm.filter(primary_role='debater').count()
        context['crm_adjudicators'] = crm.filter(primary_role='adjudicator').count()
        context['crm_tab_directors'] = crm.filter(primary_role='tab_director').count()
        context['crm_hybrid'] = crm.filter(primary_role='hybrid').count()
        context['crm_subscribed'] = crm.filter(email_subscribed=True).count()
        context['crm_with_email'] = crm.exclude(email='').count()
        context['crm_new_30d'] = crm.filter(first_seen__gte=last_30d).count()
        context['crm_recent'] = crm.order_by('-first_seen')[:8]

        return context


@method_decorator(cache_page(60), name='dispatch')
class DonationsAnalyticsView(SuperuserRequiredMixin, TemplateView):
    """Donations-focused analytics dashboard sourced from Lemon webhook data."""
    template_name = 'analytics/donations.html'

    @staticmethod
    def _refund_sum_expression():
        return Sum(
            Case(
                When(refunded_amount__gt=0, then=F('refunded_amount')),
                When(status=DonationTransaction.Status.REFUNDED, then=F('amount')),
                default=Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        period = self.request.GET.get('period', '365').strip().lower()
        transactions = DonationTransaction.objects.exclude(
            status__in=[DonationTransaction.Status.FAILED, DonationTransaction.Status.CANCELLED]
        )

        if period != 'all' and period.isdigit():
            since = now - timedelta(days=int(period))
            transactions = transactions.filter(
                Q(donated_at__gte=since)
                | Q(donated_at__isnull=True, first_seen_at__gte=since)
            )

        paid_like = transactions.filter(
            status__in=[DonationTransaction.Status.PAID, DonationTransaction.Status.REFUNDED]
        )

        totals = paid_like.aggregate(
            gross_amount=Sum('amount'),
            refunded_amount=self._refund_sum_expression(),
            transaction_count=Count('id'),
        )

        gross_amount = totals['gross_amount'] or Decimal('0.00')
        refunded_amount = totals['refunded_amount'] or Decimal('0.00')
        net_amount = gross_amount - refunded_amount
        if net_amount < Decimal('0.00'):
            net_amount = Decimal('0.00')

        refunded_tx_count = paid_like.filter(
            Q(status=DonationTransaction.Status.REFUNDED)
            | Q(refunded_amount__gt=0)
        ).count()

        transaction_count = totals['transaction_count'] or 0
        refund_rate = round((refunded_tx_count / transaction_count) * 100, 2) if transaction_count else 0

        unique_email_donors = paid_like.exclude(donor_email='').values('donor_email').distinct().count()
        unique_name_only_donors = paid_like.filter(donor_email='').exclude(donor_name='').values('donor_name').distinct().count()
        unique_donors = unique_email_donors + unique_name_only_donors

        active_supporters = transactions.filter(
            donation_type=DonationTransaction.DonationType.SUBSCRIPTION,
            status=DonationTransaction.Status.PAID,
        ).filter(
            Q(donated_at__gte=now - timedelta(days=30))
            | Q(donated_at__isnull=True, first_seen_at__gte=now - timedelta(days=30))
        ).exclude(donor_email='').values('donor_email').distinct().count()

        monthly_rows = paid_like.annotate(
            month=TruncMonth(Coalesce('donated_at', 'first_seen_at'))
        ).values('month').annotate(
            gross_amount=Sum('amount'),
            refunded_amount=self._refund_sum_expression(),
            donation_count=Count('id'),
        ).order_by('month')

        monthly_chart = {
            'labels': [],
            'gross': [],
            'net': [],
            'refunded': [],
        }
        monthly_table = []

        for row in monthly_rows:
            month = row['month']
            if month is None:
                continue

            month_label = month.strftime('%b %Y')
            gross = row['gross_amount'] or Decimal('0.00')
            refunded = row['refunded_amount'] or Decimal('0.00')
            net = gross - refunded
            if net < Decimal('0.00'):
                net = Decimal('0.00')

            monthly_chart['labels'].append(month_label)
            monthly_chart['gross'].append(float(gross))
            monthly_chart['net'].append(float(net))
            monthly_chart['refunded'].append(float(refunded))

            monthly_table.append({
                'label': month_label,
                'gross': gross,
                'net': net,
                'refunded': refunded,
                'count': row['donation_count'],
            })

        top_donors = paid_like.exclude(donor_email='').values('donor_email').annotate(
            donor_name=Max('donor_name'),
            total_donated=Sum('amount'),
            donation_count=Count('id'),
            last_donated=Max('donated_at'),
        ).order_by('-total_donated')[:10]

        recent_donations = transactions.order_by('-donated_at', '-updated_at')[:25]

        status_breakdown = list(
            transactions.values('status').annotate(count=Count('id')).order_by('-count')
        )

        context.update({
            'active_nav': 'donations',
            'period': period,
            'gross_amount': gross_amount,
            'refunded_amount': refunded_amount,
            'net_amount': net_amount,
            'refund_rate': refund_rate,
            'transaction_count': transaction_count,
            'unique_donors': unique_donors,
            'active_supporters': active_supporters,
            'monthly_chart_data': json.dumps(monthly_chart),
            'monthly_table': monthly_table,
            'top_donors': top_donors,
            'recent_donations': recent_donations,
            'status_breakdown': status_breakdown,
        })
        return context


class UsersListView(SuperuserRequiredMixin, ListView):
    """List all users with detailed information."""
    template_name = 'analytics/users_list.html'
    context_object_name = 'users'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'superuser':
            queryset = queryset.filter(is_superuser=True)
        elif status == 'staff':
            queryset = queryset.filter(is_staff=True)
        elif status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['total_users'] = User.objects.count()
        context['users_with_email'] = User.objects.exclude(email='').exclude(email__isnull=True).count()
        return context


class TournamentsListView(SuperuserRequiredMixin, ListView):
    """List all tournaments with creator and stats."""
    template_name = 'analytics/tournaments_list.html'
    context_object_name = 'tournaments'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Tournament.objects.select_related('owner').annotate(
            num_rounds=Count('round'),
            num_completed_rounds=Count('round', filter=Q(round__completed=True)),
            num_debates=Count('round__debate', distinct=True),
            num_speakers=Count('team__speaker', distinct=True),
            num_adjudicators=Count('adjudicator', distinct=True),
        ).order_by('-id')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(short_name__icontains=search) |
                Q(owner__username__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(active=True)
        elif status == 'inactive':
            queryset = queryset.filter(active=False)
        elif status == 'live':
            # "Live" = active tournament with at least one round that has
            # draw_status == 'R' (released) and is not completed
            queryset = queryset.filter(
                active=True,
                round__draw_status=Round.Status.RELEASED,
                round__completed=False,
            ).distinct()
        elif status == 'broken':
            # Filter to tournaments whose slugs are not DNS-safe
            # (these will have broken subdomain links)
            queryset = queryset.filter(
                Q(slug__contains='_') |
                Q(slug__startswith='-') |
                Q(slug__endswith='-') |
                Q(slug='')
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['total_tournaments'] = Tournament.objects.count()
        context['active_tournaments'] = Tournament.objects.filter(active=True).count()
        # Live tournaments: active with at least one unreleased/in-progress round
        context['live_tournaments'] = Tournament.objects.filter(
            active=True,
            round__draw_status=Round.Status.RELEASED,
            round__completed=False,
        ).distinct().count()
        # Count tournaments with potentially broken slugs (not DNS-safe)
        context['broken_slug_count'] = Tournament.objects.filter(
            Q(slug__contains='_') |
            Q(slug__startswith='-') |
            Q(slug__endswith='-') |
            Q(slug='')
        ).count()
        return context


class LiveVisitorsAPIView(SuperuserRequiredMixin, View):
    """API endpoint for real-time visitor count."""
    
    def get(self, request):
        ActiveSession.cleanup_stale()
        sessions = ActiveSession.objects.exclude(current_path='/health/').select_related('user')
        total_count = sessions.count()

        return JsonResponse({
            'count': total_count,
            'visitors': [
                {
                    'path': s.current_path,
                    'country': s.country,
                    'city': s.city,
                    'user': s.user.username if s.user else None,
                    'duration': str(timezone.now() - s.started_at).split('.')[0],
                }
                for s in sessions[:20]
            ]
        })


class TrafficChartAPIView(SuperuserRequiredMixin, View):
    """API endpoint for traffic chart data."""
    
    def get(self, request):
        period = request.GET.get('period', '24h')
        
        if period == '24h':
            since = timezone.now() - timedelta(hours=24)
            data = PageView.objects.filter(
                timestamp__gte=since
            ).annotate(
                period=TruncHour('timestamp')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
            labels = [d['period'].strftime('%H:%M') for d in data]
        elif period == '7d':
            since = timezone.now() - timedelta(days=7)
            data = PageView.objects.filter(
                timestamp__gte=since
            ).annotate(
                period=TruncDate('timestamp')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
            labels = [str(d['period']) for d in data]
        else:  # 30d
            since = timezone.now() - timedelta(days=30)
            data = PageView.objects.filter(
                timestamp__gte=since
            ).annotate(
                period=TruncDate('timestamp')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
            labels = [str(d['period']) for d in data]
        
        return JsonResponse({
            'labels': labels,
            'data': [d['count'] for d in data]
        })


class ExportUsersView(SuperuserRequiredMixin, View):
    """Export all users with emails as CSV (POST only for CSRF protection)."""

    def post(self, request):
        import csv
        from django.http import HttpResponse

        logger.info("User export triggered by %s from %s",
                    request.user.username, request.META.get('REMOTE_ADDR'))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="nekotab_users.csv"'

        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Date Joined', 'Last Login', 'Is Active', 'Is Staff', 'Is Superuser'])

        for user in User.objects.all().iterator():
            writer.writerow([
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                user.date_joined.strftime('%Y-%m-%d %H:%M') if user.date_joined else '',
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
                'Yes' if user.is_active else 'No',
                'Yes' if user.is_staff else 'No',
                'Yes' if user.is_superuser else 'No',
            ])
        
        return response


# ---------------------------------------------------------------------------
# Database Usage Analytics
# ---------------------------------------------------------------------------

DB_USAGE_CACHE_KEY = 'analytics_db_usage_v1'
DB_USAGE_CACHE_TTL = 60 * 15  # 15 minutes


def _get_db_usage_data():
    """Compute per-tournament database usage metrics.

    Returns a dict with keys:
        tournaments  – list of per-tournament dicts, sorted by total_rows desc
        totals       – aggregate totals across all tournaments
        db_size      – overall database size info (or None)
        cached_at    – ISO timestamp of when the data was generated
    """
    from draw.models import Debate, DebateTeam
    from adjallocation.models import DebateAdjudicator
    from participants.models import Team, Speaker, Adjudicator

    all_tournaments = Tournament.objects.all().order_by('id')
    tournament_map = {t.id: t for t in all_tournaments}
    tournament_ids = list(tournament_map.keys())

    # ------------------------------------------------------------------
    # Row counts grouped by tournament
    # ------------------------------------------------------------------

    # Direct FK to tournament
    teams_by_t = dict(
        Team.objects.filter(tournament_id__in=tournament_ids)
        .values('tournament_id')
        .annotate(count=Count('id'))
        .values_list('tournament_id', 'count')
    )
    # Speaker → Team → Tournament
    speakers_by_t = dict(
        Speaker.objects.filter(team__tournament_id__in=tournament_ids)
        .values('team__tournament_id')
        .annotate(count=Count('id'))
        .values_list('team__tournament_id', 'count')
    )
    # Adjudicator direct FK (nullable — count only those with tournament)
    adjs_by_t = dict(
        Adjudicator.objects.filter(tournament_id__in=tournament_ids)
        .values('tournament_id')
        .annotate(count=Count('id'))
        .values_list('tournament_id', 'count')
    )
    # Round → Tournament
    rounds_by_t = dict(
        Round.objects.filter(tournament_id__in=tournament_ids)
        .values('tournament_id')
        .annotate(count=Count('id'))
        .values_list('tournament_id', 'count')
    )
    # Debate → Round → Tournament
    debates_by_t = dict(
        Debate.objects.filter(round__tournament_id__in=tournament_ids)
        .values('round__tournament_id')
        .annotate(count=Count('id'))
        .values_list('round__tournament_id', 'count')
    )
    # BallotSubmission → Debate → Round → Tournament
    ballots_by_t = dict(
        BallotSubmission.objects.filter(debate__round__tournament_id__in=tournament_ids)
        .values('debate__round__tournament_id')
        .annotate(count=Count('id'))
        .values_list('debate__round__tournament_id', 'count')
    )
    # DebateTeam → Debate → Round → Tournament
    debate_teams_by_t = dict(
        DebateTeam.objects.filter(debate__round__tournament_id__in=tournament_ids)
        .values('debate__round__tournament_id')
        .annotate(count=Count('id'))
        .values_list('debate__round__tournament_id', 'count')
    )
    # DebateAdjudicator → Debate → Round → Tournament
    debate_adjs_by_t = dict(
        DebateAdjudicator.objects.filter(debate__round__tournament_id__in=tournament_ids)
        .values('debate__round__tournament_id')
        .annotate(count=Count('id'))
        .values_list('debate__round__tournament_id', 'count')
    )

    # Last activity: latest ballot timestamp per tournament
    last_activity_by_t = dict(
        BallotSubmission.objects.filter(debate__round__tournament_id__in=tournament_ids)
        .values('debate__round__tournament_id')
        .annotate(last=Max('timestamp'))
        .values_list('debate__round__tournament_id', 'last')
    )

    # ------------------------------------------------------------------
    # Estimate bytes per table (Postgres only, graceful fallback)
    # ------------------------------------------------------------------
    table_sizes = {}  # table_name → total bytes
    table_total_rows = {}  # table_name → total row count
    can_estimate_bytes = False

    if connection.vendor == 'postgresql':
        TABLE_NAMES = [
            'participants_team', 'participants_speaker', 'participants_adjudicator',
            'tournaments_round', 'draw_debate', 'results_ballotsubmission',
            'draw_debateteam', 'adjallocation_debateadjudicator',
        ]
        try:
            with connection.cursor() as cursor:
                for tbl in TABLE_NAMES:
                    cursor.execute(
                        "SELECT pg_total_relation_size(%s), "
                        "(SELECT COUNT(*) FROM {}) ".format(tbl),  # noqa: S608
                        [tbl],
                    )
                    row = cursor.fetchone()
                    if row:
                        table_sizes[tbl] = row[0] or 0
                        table_total_rows[tbl] = row[1] or 0
            can_estimate_bytes = True
        except Exception:
            can_estimate_bytes = False

    # Model → (table_name, by_t_dict)
    MODEL_MAP = [
        ('teams', 'participants_team', teams_by_t),
        ('speakers', 'participants_speaker', speakers_by_t),
        ('adjudicators', 'participants_adjudicator', adjs_by_t),
        ('rounds', 'tournaments_round', rounds_by_t),
        ('debates', 'draw_debate', debates_by_t),
        ('ballots', 'results_ballotsubmission', ballots_by_t),
        ('debate_teams', 'draw_debateteam', debate_teams_by_t),
        ('debate_adjs', 'adjallocation_debateadjudicator', debate_adjs_by_t),
    ]

    # ------------------------------------------------------------------
    # Build per-tournament breakdown
    # ------------------------------------------------------------------
    results = []
    grand_total_rows = 0
    grand_total_bytes = 0

    for tid, t in tournament_map.items():
        breakdown = {}
        total_rows = 0
        total_bytes = 0.0

        for label, table_name, by_t in MODEL_MAP:
            row_count = by_t.get(tid, 0)
            breakdown[label] = {'rows': row_count}
            total_rows += row_count

            if can_estimate_bytes and table_total_rows.get(table_name, 0) > 0:
                share = row_count / table_total_rows[table_name]
                est_bytes = share * table_sizes[table_name]
                breakdown[label]['bytes'] = int(est_bytes)
                total_bytes += est_bytes
            else:
                breakdown[label]['bytes'] = None

        impact_score = total_rows + (total_bytes / 1024 if total_bytes else 0)

        results.append({
            'id': t.id,
            'slug': t.slug,
            'name': t.name,
            'active': t.active,
            'total_rows': total_rows,
            'total_bytes': int(total_bytes) if can_estimate_bytes else None,
            'total_mb': round(total_bytes / (1024 * 1024), 2) if can_estimate_bytes else None,
            'impact_score': round(impact_score, 1),
            'breakdown': breakdown,
            'last_activity': last_activity_by_t.get(tid),
        })

        grand_total_rows += total_rows
        grand_total_bytes += total_bytes

    results.sort(key=lambda r: r['total_rows'], reverse=True)

    # ------------------------------------------------------------------
    # Overall DB size (Postgres only)
    # ------------------------------------------------------------------
    db_size = None
    if connection.vendor == 'postgresql':
        try:
            with connection.cursor() as cursor:
                db_name = settings.DATABASES['default']['NAME']
                cursor.execute("SELECT pg_database_size(%s)", [db_name])
                raw = cursor.fetchone()[0]
                db_size = {
                    'bytes': raw,
                    'mb': round(raw / (1024 * 1024), 2),
                    'gb': round(raw / (1024 * 1024 * 1024), 3),
                }
        except Exception:
            pass

    return {
        'tournaments': results,
        'totals': {
            'rows': grand_total_rows,
            'bytes': int(grand_total_bytes) if can_estimate_bytes else None,
            'mb': round(grand_total_bytes / (1024 * 1024), 2) if can_estimate_bytes else None,
            'tournament_count': len(results),
        },
        'db_size': db_size,
        'can_estimate_bytes': can_estimate_bytes,
        'cached_at': timezone.now().isoformat(),
    }


class DbUsageView(SuperuserRequiredMixin, TemplateView):
    """Per-tournament database usage analytics."""
    template_name = 'analytics/db_usage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Try cache first
        data = cache.get(DB_USAGE_CACHE_KEY)
        if data is None:
            data = _get_db_usage_data()
            cache.set(DB_USAGE_CACHE_KEY, data, DB_USAGE_CACHE_TTL)

        # Apply filters
        tournaments = data['tournaments']

        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            tournaments = [t for t in tournaments if t['active']]
        elif status_filter == 'inactive':
            tournaments = [t for t in tournaments if not t['active']]

        search = self.request.GET.get('search', '').strip().lower()
        if search:
            tournaments = [
                t for t in tournaments
                if search in t['slug'].lower() or search in t['name'].lower()
            ]

        top_n = self.request.GET.get('top', '')
        if top_n and top_n.isdigit():
            tournaments = tournaments[:int(top_n)]

        context.update({
            'usage_data': tournaments,
            'totals': data['totals'],
            'db_size': data['db_size'],
            'can_estimate_bytes': data['can_estimate_bytes'],
            'cached_at': data['cached_at'],
            'search': self.request.GET.get('search', ''),
            'status': status_filter,
            'top': top_n,
        })
        return context


class RefreshDbUsageCacheView(SuperuserRequiredMixin, View):
    """Clear DB usage cache and redirect back."""

    def post(self, request):
        cache.delete(DB_USAGE_CACHE_KEY)
        return redirect('analytics:db_usage')


class DeleteTournamentsView(SuperuserRequiredMixin, View):
    """Hard-delete one or more tournaments and log the audit trail."""

    def post(self, request):
        from django.core.mail import send_mail
        from django.db import transaction as db_transaction
        from retention.engine import _clear_protect_refs, _clear_caches, _snapshot_counts, _owner_info
        from retention.models import TournamentDeletionLog

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

        raw_ids = body.get('tournament_ids', [])
        if not raw_ids or not isinstance(raw_ids, list):
            return JsonResponse({'error': 'tournament_ids must be a non-empty list.'}, status=400)

        # Sanitise to ints
        try:
            tournament_ids = [int(tid) for tid in raw_ids]
        except (TypeError, ValueError):
            return JsonResponse({'error': 'All tournament_ids must be integers.'}, status=400)

        tournaments = Tournament.objects.filter(id__in=tournament_ids)
        if not tournaments.exists():
            return JsonResponse({'error': 'No matching tournaments found.'}, status=404)

        deleted = []
        failed = []

        for t in tournaments:
            owner_email, owner_username = _owner_info(t)
            counts = _snapshot_counts(t)
            slug = t.slug
            tid = t.id
            name = t.name

            try:
                with db_transaction.atomic():
                    _clear_protect_refs(t)
                    _clear_caches(t)
                    t.delete()

                TournamentDeletionLog.objects.create(
                    tournament_id=tid, slug=slug, name=name,
                    owner_email=owner_email, owner_username=owner_username,
                    status=TournamentDeletionLog.Status.DELETED,
                    **counts,
                )
                deleted.append({'id': tid, 'slug': slug, 'name': name})
                logger.info("Dashboard hard-delete: %s (id=%d) by %s",
                            slug, tid, request.user.username)

                # Notify the owner via email
                if owner_email:
                    try:
                        send_mail(
                            f'[NekoTab] Tournament "{name}" has been deleted',
                            f'Hi {owner_username or "there"},\n\n'
                            f'Your tournament "{name}" ({slug}) has been permanently '
                            f'deleted by an administrator ({request.user.username}).\n\n'
                            f'Summary at time of deletion:\n'
                            f'  Teams: {counts["team_count"]}\n'
                            f'  Rounds: {counts["round_count"]}\n'
                            f'  Debates: {counts["debate_count"]}\n\n'
                            f'If you believe this was done in error, please contact '
                            f'the site administrator.\n\n'
                            f'— NekoTab',
                            settings.DEFAULT_FROM_EMAIL,
                            [owner_email],
                            fail_silently=True,
                        )
                    except Exception:
                        logger.exception("Failed to send deletion email for %s to %s",
                                         slug, owner_email)

            except Exception as exc:
                logger.exception("Failed to delete tournament %s (id=%d)", slug, tid)
                TournamentDeletionLog.objects.create(
                    tournament_id=tid, slug=slug, name=name,
                    owner_email=owner_email, owner_username=owner_username,
                    status=TournamentDeletionLog.Status.FAILED,
                    error_message=str(exc),
                    **counts,
                )
                failed.append({'id': tid, 'slug': slug, 'error': 'Deletion failed. Check server logs for details.'})

        # Bust the DB-usage cache so refreshed data appears immediately
        cache.delete(DB_USAGE_CACHE_KEY)

        return JsonResponse({
            'deleted': deleted,
            'failed': failed,
            'deleted_count': len(deleted),
            'failed_count': len(failed),
        })


class DeleteUsersView(SuperuserRequiredMixin, View):
    """Hard-delete one or more users. Superusers cannot be deleted."""

    def post(self, request):
        from django.db import transaction as db_transaction

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

        raw_ids = body.get('user_ids', [])
        if not raw_ids or not isinstance(raw_ids, list):
            return JsonResponse({'error': 'user_ids must be a non-empty list.'}, status=400)

        try:
            user_ids = [int(uid) for uid in raw_ids]
        except (TypeError, ValueError):
            return JsonResponse({'error': 'All user_ids must be integers.'}, status=400)

        # Never allow deleting the requesting user or any superuser
        users = User.objects.filter(id__in=user_ids)
        if not users.exists():
            return JsonResponse({'error': 'No matching users found.'}, status=404)

        deleted = []
        skipped = []
        failed = []

        for u in users:
            if u.id == request.user.id:
                skipped.append({'id': u.id, 'username': u.username, 'reason': 'Cannot delete yourself.'})
                continue
            if u.is_superuser:
                skipped.append({'id': u.id, 'username': u.username, 'reason': 'Cannot delete a superuser.'})
                continue

            uid = u.id
            username = u.username
            email = u.email

            try:
                with db_transaction.atomic():
                    u.delete()
                deleted.append({'id': uid, 'username': username, 'email': email})
                logger.info("User deleted: %s (id=%d) by %s", username, uid, request.user.username)
            except Exception as exc:
                logger.exception("Failed to delete user %s (id=%d)", username, uid)
                failed.append({'id': uid, 'username': username, 'error': str(exc)})

        return JsonResponse({
            'deleted': deleted,
            'skipped': skipped,
            'failed': failed,
            'deleted_count': len(deleted),
            'skipped_count': len(skipped),
            'failed_count': len(failed),
        })


# ==============================================================================
# Motion Bank — Bulk CSV Upload (superuser only)
# ==============================================================================

class MotionBulkUploadView(SuperuserRequiredMixin, View):
    """Accept a CSV file and bulk-create MotionEntry records in the motion bank.

    Expected CSV columns (header row required):
      text, format, tournament_name, year, region, round_info, info_slide, difficulty

    Only 'text' is strictly required. All others are optional and will use
    sensible defaults if omitted or blank.
    """

    ALLOWED_FORMATS = {c.value for c in MotionEntry.MotionFormat}
    FORMAT_DISPLAY = {c.value: c.label for c in MotionEntry.MotionFormat}

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('analytics:dashboard')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Only .csv files are accepted.')
            return redirect('analytics:dashboard')

        try:
            decoded = csv_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, 'CSV file must be UTF-8 encoded.')
            return redirect('analytics:dashboard')

        reader = csv.DictReader(io.StringIO(decoded))
        if 'text' not in (reader.fieldnames or []):
            messages.error(request, 'CSV must have a "text" column.')
            return redirect('analytics:dashboard')

        created = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, start=2):  # row 1 is header
            text = row.get('text', '').strip()
            if not text:
                skipped += 1
                continue

            fmt = row.get('format', 'bp').strip().lower()
            if fmt not in self.ALLOWED_FORMATS:
                fmt = 'bp'

            year_raw = row.get('year', '').strip()
            try:
                year = int(year_raw) if year_raw else None
            except ValueError:
                year = None

            difficulty_raw = row.get('difficulty', '3').strip()
            try:
                difficulty = int(difficulty_raw)
                if difficulty not in range(1, 6):
                    difficulty = 3
            except ValueError:
                difficulty = 3

            # Build a unique slug from the first 80 chars of text
            base_slug = slugify(text[:80])
            slug = base_slug
            suffix = 1
            while MotionEntry.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            try:
                MotionEntry.objects.create(
                    text=text,
                    slug=slug,
                    format=fmt,
                    tournament_name=row.get('tournament_name', '').strip()[:200],
                    year=year,
                    region=row.get('region', '').strip()[:100],
                    round_info=row.get('round_info', '').strip()[:100],
                    info_slide=row.get('info_slide', '').strip(),
                    difficulty=difficulty,
                )
                created += 1
            except Exception as exc:
                errors.append(f"Row {i}: {exc}")

        if errors:
            messages.warning(
                request,
                f'Imported {created} motions, skipped {skipped} blank rows, '
                f'{len(errors)} errors: ' + '; '.join(errors[:3]),
            )
        else:
            messages.success(
                request,
                f'Successfully imported {created} motions to the Motion Bank'
                + (f' ({skipped} blank rows skipped).' if skipped else '.'),
            )

        return redirect('analytics:dashboard')


# =============================================================================
# Tournament Motion Harvest — push hosted-tournament motions to the motion bank
# =============================================================================

class TournamentMotionsView(SuperuserRequiredMixin, TemplateView):
    """List all DB-backed tournament motions; show which are already in the bank."""
    template_name = 'analytics/tournament_motions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from motions.models import Motion
        from django.db.models import Exists, OuterRef
        import collections

        already_banked = MotionEntry.objects.filter(internal_motion=OuterRef('pk'))
        motions_qs = (
            Motion.objects
            .select_related('tournament')
            .prefetch_related('rounds')
            .annotate(in_bank=Exists(already_banked))
            .order_by('-tournament__id', 'id')
        )

        grouped = collections.OrderedDict()
        for m in motions_qs:
            tid = m.tournament_id
            if tid not in grouped:
                grouped[tid] = {'tournament': m.tournament, 'motions': []}
            year = None
            round_names = []
            for r in m.rounds.all():
                round_names.append(r.name)
                if year is None and getattr(r, 'starts_at', None):
                    year = r.starts_at.year
            grouped[tid]['motions'].append({
                'id': m.id,
                'text': m.text,
                'info_slide': m.info_slide or '',
                'reference': m.reference,
                'rounds': round_names,
                'in_bank': m.in_bank,
                'year': year,
            })

        tournament_groups = list(grouped.values())
        context['tournament_groups'] = tournament_groups
        context['total_pending'] = sum(
            sum(1 for m in g['motions'] if not m['in_bank']) for g in tournament_groups
        )
        context['total_banked'] = sum(
            sum(1 for m in g['motions'] if m['in_bank']) for g in tournament_groups
        )
        return context


class PushMotionToBankView(SuperuserRequiredMixin, View):
    """POST {motion_ids: [int, ...]} — push tournament motions into the flat-file motion bank."""

    _FORMAT_MAP = {
        'bp':     ('bp', 'BP'),
        'ap':     ('ap', 'Asians/Australs'),
        'wsdc':   ('wsdc', 'World Schools'),
        'pf':     ('pf', 'Public Forum'),
        'ld':     ('ld', 'Lincoln-Douglas'),
        'policy': ('policy', 'Policy'),
        'cp':     ('cp', 'BP'),
    }

    @staticmethod
    def _detect_motion_type(text):
        t = text.strip().upper()
        if t.startswith('THBT ') or t.startswith('THIS HOUSE BELIEVES THAT '):
            return 'thbt'
        if t.startswith('THW ') or t.startswith('THIS HOUSE WOULD '):
            return 'thw'
        if t.startswith('THR ') or t.startswith('THIS HOUSE REGRETS '):
            return 'thr'
        if t.startswith('THS ') or t.startswith('THIS HOUSE SUPPORTS '):
            return 'ths'
        if t.startswith('THB ') or t.startswith('THIS HOUSE BELIEVES '):
            return 'thb'
        if t.startswith('RESOLVED:') or t.startswith('RESOLVED '):
            return 'policy'
        return 'thbt'

    def post(self, request):
        import uuid as uuid_mod
        import datetime as dt
        from motions.models import Motion
        from django.utils.text import slugify
        from motionbank.views import _MOTIONS_CACHE, _MOTIONS_SEO_CACHE

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        raw_ids = body.get('motion_ids', [])
        if not raw_ids or not isinstance(raw_ids, list):
            return JsonResponse({'error': 'motion_ids must be a non-empty list'}, status=400)
        try:
            motion_ids = [int(mid) for mid in raw_ids]
        except (TypeError, ValueError):
            return JsonResponse({'error': 'All motion_ids must be integers'}, status=400)

        motions = (
            Motion.objects
            .select_related('tournament')
            .prefetch_related('rounds')
            .filter(id__in=motion_ids)
        )
        if not motions.exists():
            return JsonResponse({'error': 'No matching motions found'}, status=404)

        pushed = []
        skipped = []
        new_json_entries = []

        for motion in motions:
            if MotionEntry.objects.filter(internal_motion=motion).exists():
                skipped.append({'id': motion.id, 'reason': 'Already in bank'})
                continue

            # Detect debate format from tournament preferences (fallback BP)
            fmt_code, fmt_style = 'bp', 'BP'
            try:
                pref_rules = motion.tournament.preferences.get_by_name('debate_rules')
                if pref_rules and pref_rules.value in self._FORMAT_MAP:
                    fmt_code, fmt_style = self._FORMAT_MAP[pref_rules.value]
            except Exception:
                pass

            motion_type = self._detect_motion_type(motion.text)

            # Year and round names from associated rounds
            year = None
            round_names = []
            for r in motion.rounds.all():
                round_names.append(r.name)
                if year is None and getattr(r, 'starts_at', None):
                    year = r.starts_at.year

            # Build unique slug
            base_slug = slugify(motion.text[:80]) or slugify(motion.reference[:80]) or 'motion'
            slug = base_slug
            counter = 1
            while MotionEntry.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            entry = MotionEntry.objects.create(
                text=motion.text,
                slug=slug,
                info_slide=motion.info_slide or '',
                format=fmt_code,
                motion_type=motion_type,
                tournament_name=motion.tournament.name,
                year=year,
                round_info=', '.join(round_names),
                source=f'nekotab:{motion.tournament.slug}',
                internal_motion=motion,
                is_approved=True,
                submitted_by=request.user,
            )

            # Build flat-file JSON entry (schema matches motions-version-01.json)
            start_date = f'{year}-01-01T00:00:00+00:00' if year else ''
            json_entry = {
                'id': str(uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, f'nekotab-motion:{motion.id}')),
                'tournament_id': str(uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, f'nekotab-tournament:{motion.tournament.id}')),
                'tournament_name': motion.tournament.name,
                'motion': motion.text,
                'infoslide': motion.info_slide or '',
                'untranslated_motion': '',
                'untranslated_infoslide': '',
                'round': ', '.join(round_names),
                'round_type': '',
                'motion_type': motion_type.upper(),
                'types': [],
                'primary_types': [],
                'secondary_types': None,
                'bias': 'neutral',
                'bias_burden_pro': 5, 'bias_burden_opp': 5,
                'bias_ground_pro': 5, 'bias_ground_opp': 5,
                'difficulty_technical': 5, 'difficulty_complexity': 5,
                'difficulty_abstraction': 5, 'difficulty_depth': 5,
                'start_date': start_date,
                'end_date': None,
                'region': '',
                'country': '',
                'city': '',
                'level': 'University',
                'style': fmt_style,
                'tab_url': f'/t/{motion.tournament.slug}/',
                'video_urls': [],
                'adjudicators': None,
                'created_at': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00'),
            }
            new_json_entries.append(json_entry)
            pushed.append({'id': motion.id, 'text': motion.text[:80], 'entry_id': entry.id})

        # Append to flat JSON file and bust in-process caches
        if new_json_entries:
            json_path = os.path.join(
                os.path.dirname(settings.BASE_DIR),
                'Motion-Bank',
                'motions-version-01.json',
            )
            try:
                with open(json_path, encoding='utf-8') as f:
                    flat_data = json.load(f)
                flat_data.extend(new_json_entries)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(flat_data, f, ensure_ascii=False, separators=(',', ':'))
                _MOTIONS_CACHE['data'] = None
                _MOTIONS_SEO_CACHE['context'] = None
                logger.info('Motion Harvest: appended %d entries to flat JSON', len(new_json_entries))
            except Exception:
                logger.exception('Motion Harvest: failed to update flat JSON file')
                # DB entries are still created; don't fail the response

        return JsonResponse({
            'pushed': pushed,
            'skipped': skipped,
            'pushed_count': len(pushed),
            'skipped_count': len(skipped),
        })
