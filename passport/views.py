import logging
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    DebatePassport, TournamentParticipation, RoundPerformance,
    JudgeBallot, Partnership, UserStats,
)
from .serializers import (
    DebatePassportListSerializer, DebatePassportDetailSerializer,
    DebatePassportUpdateSerializer,
    TournamentParticipationSerializer, TournamentParticipationCreateSerializer,
    RoundPerformanceSerializer, JudgeBallotSerializer,
    PartnershipSerializer, UserStatsSerializer,
)
from .analytics import recompute_user_stats, compute_partnerships

logger = logging.getLogger(__name__)


# =============================================================================
# Template Views
# =============================================================================

class PassportDirectoryView(TemplateView):
    template_name = 'passport/passport_directory.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Debate Passports'
        context['page_emoji'] = '🌍'
        return context


class PassportProfileView(TemplateView):
    template_name = 'passport/passport_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = kwargs.get('user_id')
        try:
            passport = DebatePassport.objects.select_related('user', 'cached_stats').get(user_id=user_id)
            if not passport.is_public and self.request.user.id != user_id:
                context['page_title'] = 'Private Profile'
                context['is_private'] = True
            else:
                context['passport'] = passport
                context['page_title'] = passport.display_name
                context['page_emoji'] = '🎓'
        except DebatePassport.DoesNotExist:
            context['page_title'] = 'Passport Not Found'
        return context


class PassportEditView(LoginRequiredMixin, TemplateView):
    template_name = 'passport/passport_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit Your Passport'
        context['page_emoji'] = '✏️'
        return context


class PassportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'passport/passport_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Your Analytics Dashboard'
        context['page_emoji'] = '📊'
        return context


# =============================================================================
# API Views
# =============================================================================

class PassportListAPI(generics.ListAPIView):
    """Browse public debate passports."""
    serializer_class = DebatePassportListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = DebatePassport.objects.filter(is_public=True).select_related('user')

        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country__icontains=country)

        fmt = self.request.query_params.get('format')
        if fmt:
            qs = qs.filter(primary_format=fmt)

        institution = self.request.query_params.get('institution')
        if institution:
            qs = qs.filter(institution__icontains=institution)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(display_name__icontains=search)

        return qs


class PassportDetailAPI(generics.RetrieveAPIView):
    """View a full debate passport with all data."""
    serializer_class = DebatePassportDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return DebatePassport.objects.select_related('user', 'cached_stats').prefetch_related(
            'participations__round_performances',
            'participations__judge_ballots',
            'partnerships',
            'user__forum_badges',
        )

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        passport = get_object_or_404(self.get_queryset(), user_id=user_id)

        # Check privacy
        if not passport.is_public and self.request.user.id != passport.user_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This profile is private.")

        return passport


class PassportMeAPI(generics.RetrieveUpdateAPIView):
    """View/edit your own passport."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return DebatePassportUpdateSerializer
        return DebatePassportDetailSerializer

    def get_object(self):
        passport, created = DebatePassport.objects.get_or_create(
            user=self.request.user,
            defaults={'display_name': self.request.user.username},
        )
        if created:
            UserStats.objects.create(passport=passport)
        return passport


class TournamentParticipationListAPI(generics.ListCreateAPIView):
    """List/add tournament participations to your passport."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        passport = DebatePassport.objects.filter(user=self.request.user).first()
        if passport is None:
            return TournamentParticipation.objects.none()
        return TournamentParticipation.objects.filter(passport=passport).prefetch_related(
            'round_performances', 'judge_ballots',
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TournamentParticipationCreateSerializer
        return TournamentParticipationSerializer

    def perform_create(self, serializer):
        passport, _ = DebatePassport.objects.get_or_create(
            user=self.request.user,
            defaults={'display_name': self.request.user.username},
        )
        serializer.save(passport=passport)


class TournamentParticipationDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """View/edit/delete a tournament participation."""
    serializer_class = TournamentParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        passport = DebatePassport.objects.filter(user=self.request.user).first()
        if passport is None:
            return TournamentParticipation.objects.none()
        return TournamentParticipation.objects.filter(passport=passport)


class RoundPerformanceListAPI(generics.ListCreateAPIView):
    """Add round performances to a tournament participation."""
    serializer_class = RoundPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        participation_id = self.kwargs.get('participation_id')
        return RoundPerformance.objects.filter(
            participation_id=participation_id,
            participation__passport__user=self.request.user,
        )

    def perform_create(self, serializer):
        participation = get_object_or_404(
            TournamentParticipation,
            pk=self.kwargs['participation_id'],
            passport__user=self.request.user,
        )
        serializer.save(participation=participation)


class JudgeBallotListAPI(generics.ListCreateAPIView):
    """Add judge ballots to a tournament participation."""
    serializer_class = JudgeBallotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        participation_id = self.kwargs.get('participation_id')
        return JudgeBallot.objects.filter(
            participation_id=participation_id,
            participation__passport__user=self.request.user,
        )

    def perform_create(self, serializer):
        participation = get_object_or_404(
            TournamentParticipation,
            pk=self.kwargs['participation_id'],
            passport__user=self.request.user,
        )
        serializer.save(participation=participation)


class RecomputeStatsAPI(APIView):
    """Trigger recomputation of user analytics."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            passport = DebatePassport.objects.get(user=request.user)
            stats = recompute_user_stats(passport)
            compute_partnerships(passport)
            return Response({
                'status': 'ok',
                'stats': UserStatsSerializer(stats).data,
            })
        except DebatePassport.DoesNotExist:
            return Response(
                {'error': 'No passport found. Create your passport first.'},
                status=status.HTTP_404_NOT_FOUND,
            )


class PartnershipListAPI(generics.ListAPIView):
    """View partnership analytics."""
    serializer_class = PartnershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        passport = DebatePassport.objects.filter(user=self.request.user).first()
        if passport is None:
            return Partnership.objects.none()
        return Partnership.objects.filter(passport=passport)


class LeaderboardAPI(APIView):
    """Global debate leaderboard (top speakers, judges)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category = request.query_params.get('category', 'speakers')
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
        except (ValueError, TypeError):
            limit = 20

        if category == 'speakers':
            top = UserStats.objects.filter(
                passport__is_public=True,
                total_tournaments__gte=3,
            ).select_related('passport').order_by('-average_speaker_score')[:limit]

            return Response([{
                'display_name': s.passport.display_name,
                'country': s.passport.country,
                'country_code': s.passport.country_code,
                'institution': s.passport.institution,
                'user_id': s.passport.user_id,
                'avg_score': s.average_speaker_score,
                'tournaments': s.total_tournaments,
                'win_rate': s.overall_win_rate,
                'break_rate': s.break_rate,
            } for s in top])

        elif category == 'judges':
            top = UserStats.objects.filter(
                passport__is_public=True,
                judge_total_rounds__gte=10,
            ).select_related('passport').order_by('-judge_majority_agreement')[:limit]

            return Response([{
                'display_name': s.passport.display_name,
                'country': s.passport.country,
                'country_code': s.passport.country_code,
                'user_id': s.passport.user_id,
                'rounds_judged': s.judge_total_rounds,
                'chair_rate': s.judge_chair_rate,
                'agreement_rate': s.judge_majority_agreement,
            } for s in top])

        return Response({'error': 'Invalid category'}, status=400)
