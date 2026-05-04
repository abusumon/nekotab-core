import csv

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView, View

from tournaments.models import Tournament
from .models import ParticipantProfile, ParticipantTag


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/accounts/login/'
    raise_exception = False

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/')
        return super().handle_no_permission()


# ── List views ────────────────────────────────────────────────────────────────


class BaseParticipantListView(SuperuserRequiredMixin, ListView):
    """Shared base for all four participant list pages.

    Subclasses set page_title, page_emoji, active_nav, and role_filter.
    A single template renders conditionally based on context flags.
    """
    model = ParticipantProfile
    template_name = 'analytics/participants_list.html'
    context_object_name = 'profiles'
    paginate_by = 50

    page_title = 'All Participants'
    page_emoji = '👥'
    active_nav = 'participants_all'
    role_filter = None  # None = all roles

    def get_queryset(self):
        qs = ParticipantProfile.objects.all()

        if self.role_filter:
            qs = qs.filter(primary_role__in=self.role_filter)

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))

        tournament_id = self.request.GET.get('tournament')
        if tournament_id:
            qs = qs.filter(tournaments_participated__id=tournament_id)

        sub = self.request.GET.get('subscribed')
        if sub == 'yes':
            qs = qs.filter(email_subscribed=True)
        elif sub == 'no':
            qs = qs.filter(email_subscribed=False)

        tag_id = self.request.GET.get('tag')
        if tag_id:
            qs = qs.filter(tags__id=tag_id)

        activity = self.request.GET.get('activity')
        if activity:
            days_map = {'30': 30, '90': 90, '365': 365}
            days = days_map.get(activity)
            if days:
                since = timezone.now() - timezone.timedelta(days=days)
                qs = qs.filter(last_active__gte=since)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = self.page_title
        ctx['page_emoji'] = self.page_emoji
        ctx['active_nav'] = self.active_nav

        # Current filter values (for sticky form inputs)
        ctx['search'] = self.request.GET.get('search', '')
        ctx['selected_tournament'] = self.request.GET.get('tournament', '')
        ctx['selected_subscribed'] = self.request.GET.get('subscribed', '')
        ctx['selected_tag'] = self.request.GET.get('tag', '')
        ctx['selected_activity'] = self.request.GET.get('activity', '')

        # Global stats (all profiles, not just current filter)
        all_p = ParticipantProfile.objects
        ctx['total_profiles'] = all_p.count()
        ctx['total_debaters'] = all_p.filter(primary_role='debater').count()
        ctx['total_adjudicators'] = all_p.filter(primary_role='adjudicator').count()
        ctx['total_tab_directors'] = all_p.filter(primary_role='tab_director').count()
        ctx['total_hybrid'] = all_p.filter(primary_role='hybrid').count()
        ctx['total_subscribed'] = all_p.filter(email_subscribed=True).count()

        # Filter dropdowns
        ctx['tournaments'] = Tournament.objects.order_by('-created_at')[:100]
        ctx['tags'] = ParticipantTag.objects.all()

        # Column visibility flags
        rf = self.role_filter or []
        ctx['show_role_badge'] = self.role_filter is None or len(rf) > 1
        ctx['show_rounds_debated'] = not rf or 'debater' in rf or 'hybrid' in rf
        ctx['show_rounds_adjudicated'] = not rf or 'adjudicator' in rf or 'hybrid' in rf
        ctx['show_user_info'] = rf == ['tab_director']
        return ctx


class AllParticipantsView(BaseParticipantListView):
    page_title = 'All Participants'
    page_emoji = '👥'
    active_nav = 'participants_all'
    role_filter = None


class DebatersView(BaseParticipantListView):
    page_title = 'Debaters'
    page_emoji = '🎤'
    active_nav = 'participants_debaters'
    role_filter = ['debater', 'hybrid']


class AdjudicatorsView(BaseParticipantListView):
    page_title = 'Adjudicators'
    page_emoji = '⚖️'
    active_nav = 'participants_adjudicators'
    role_filter = ['adjudicator', 'hybrid']


class TabDirectorsView(BaseParticipantListView):
    page_title = 'Tab Directors'
    page_emoji = '🛡️'
    active_nav = 'participants_tab_directors'
    role_filter = ['tab_director']


# ── Actions ───────────────────────────────────────────────────────────────────


class ExportParticipantsView(SuperuserRequiredMixin, View):
    """CSV export of participants (POST for CSRF protection)."""

    def post(self, request):
        role = request.POST.get('role', '')
        qs = ParticipantProfile.objects.all()
        if role:
            qs = qs.filter(primary_role=role)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="participants.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Role', 'Rounds Debated',
                         'Rounds Adjudicated', 'Subscribed', 'Last Active'])
        for p in qs.iterator():
            writer.writerow([
                p.name, p.email, p.get_primary_role_display(),
                p.total_rounds_debated, p.total_rounds_adjudicated,
                'Yes' if p.email_subscribed else 'No',
                p.last_active.strftime('%Y-%m-%d') if p.last_active else '',
            ])
        return response


class AddTagView(SuperuserRequiredMixin, View):
    """Bulk-add a tag to selected participant profiles."""

    def post(self, request):
        profile_ids = request.POST.getlist('profile_ids')
        tag_name = request.POST.get('tag_name', '').strip()
        if not profile_ids or not tag_name:
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        tag, _ = ParticipantTag.objects.get_or_create(
            name=tag_name, defaults={'color': '#7c3aed'},
        )
        profiles = ParticipantProfile.objects.filter(id__in=profile_ids)
        for p in profiles:
            p.tags.add(tag)
        return JsonResponse({'success': True, 'count': profiles.count(), 'tag': tag.name})


class RecipientPreviewAPIView(SuperuserRequiredMixin, View):
    """API: preview recipient count for a campaign audience segment."""

    def get(self, request):
        roles = request.GET.getlist('roles')
        tournament_id = request.GET.get('tournament')
        active_since = request.GET.get('active_since')

        qs = ParticipantProfile.objects.filter(email_subscribed=True)
        if roles:
            qs = qs.filter(primary_role__in=roles)
        if tournament_id:
            qs = qs.filter(tournaments_participated__id=tournament_id)
        if active_since:
            qs = qs.filter(last_active__date__gte=active_since)
        return JsonResponse({'count': qs.distinct().count()})


# ── Public unsubscribe ────────────────────────────────────────────────────────


class UnsubscribeView(View):
    """One-click email unsubscribe (link from campaign footer).

    Uses django.core.signing for stateless, tamper-proof tokens.
    """

    def get(self, request):
        token = request.GET.get('token', '')
        data = ParticipantProfile.verify_unsubscribe_token(token)

        if not data:
            return render(request, 'participant_crm/unsubscribe.html', {
                'status': 'invalid',
                'title': 'Invalid or Expired Link',
                'message': 'This unsubscribe link is no longer valid. Links expire after one year.',
            })

        email = data.get('email', '')
        profile, _ = ParticipantProfile.objects.get_or_create(
            email=email,
            defaults={
                'name': email.split('@')[0],
                'primary_role': 'debater',
            }
        )
        if profile.email_subscribed:
            profile.email_subscribed = False
            profile.unsubscribed_at = timezone.now()
            profile.save(update_fields=['email_subscribed', 'unsubscribed_at'])

        return render(request, 'participant_crm/unsubscribe.html', {
            'status': 'success',
            'title': 'Successfully Unsubscribed',
            'message': f'{email} has been removed from NekoTab email communications.',
            'email': email,
        })
