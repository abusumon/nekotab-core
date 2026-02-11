import json
from datetime import timedelta
from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, ListView, View

from tournaments.models import Tournament, Round
from results.models import BallotSubmission
from .models import PageView, DailyStats, ActiveSession

User = get_user_model()


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only superusers can access the dashboard."""
    login_url = '/accounts/login/'
    raise_exception = False
    
    def test_func(self):
        return self.request.user.is_superuser


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
        context['device_stats'] = {d['device_type']: d['count'] for d in devices}
        
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
        queryset = Tournament.objects.select_related('owner').order_by('-id')
        
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
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['total_tournaments'] = Tournament.objects.count()
        context['active_tournaments'] = Tournament.objects.filter(active=True).count()
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
