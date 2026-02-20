import json
import logging
from datetime import timedelta
from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, ListView, View

from tournaments.models import Tournament, Round
from results.models import BallotSubmission
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
        
        # === REAL-TIME STATS ===
        ActiveSession.cleanup_stale()
        context['live_visitors'] = ActiveSession.objects.count()
        context['active_sessions'] = ActiveSession.objects.all()[:10]
        
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
        
        # Recent tournaments (ordered by id desc since Tournament has no created timestamp)
        context['recent_tournaments'] = Tournament.objects.select_related('owner').order_by('-id')[:10]
        
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
        sessions = ActiveSession.objects.all()[:20]
        
        return JsonResponse({
            'count': sessions.count(),
            'visitors': [
                {
                    'path': s.current_path,
                    'country': s.country,
                    'city': s.city,
                    'user': s.user.username if s.user else None,
                    'duration': str(timezone.now() - s.started_at).split('.')[0],
                }
                for s in sessions
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
    """Export all users with emails as CSV."""
    
    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="nekotab_users.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Date Joined', 'Last Login', 'Is Active', 'Is Staff', 'Is Superuser'])
        
        for user in User.objects.all().order_by('-date_joined'):
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

            except Exception as exc:
                logger.exception("Failed to delete tournament %s (id=%d)", slug, tid)
                TournamentDeletionLog.objects.create(
                    tournament_id=tid, slug=slug, name=name,
                    owner_email=owner_email, owner_username=owner_username,
                    status=TournamentDeletionLog.Status.FAILED,
                    error_message=str(exc),
                    **counts,
                )
                failed.append({'id': tid, 'slug': slug, 'error': str(exc)})

        # Bust the DB-usage cache so refreshed data appears immediately
        cache.delete(DB_USAGE_CACHE_KEY)

        return JsonResponse({
            'deleted': deleted,
            'failed': failed,
            'deleted_count': len(deleted),
            'failed_count': len(failed),
        })
