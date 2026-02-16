import json
import logging
from os import environ

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, F, Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MotionEntry, MotionAnalysis, MotionStats,
    MotionRating, CaseOutline, CaseOutlineVote, PracticeSession,
    MotionReport, MotionReportFeedback, Archetype,
)
from .serializers import (
    MotionEntryListSerializer, MotionEntryDetailSerializer,
    MotionEntryCreateSerializer, MotionAnalysisSerializer,
    MotionRatingSerializer, CaseOutlineSerializer,
    MotionDoctorInputSerializer, PracticeSessionSerializer,
    MotionReportFeedbackSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Template Views (SEO-friendly page shells)
# =============================================================================

class MotionBankHomeView(TemplateView):
    template_name = 'motionbank/motionbank_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Global Motion Bank'
        context['page_emoji'] = '📋'
        context['seo_keywords'] = 'debate motions, motion bank, BP motions, WSDC motions, debate topics'
        return context


class MotionDetailView(TemplateView):
    template_name = 'motionbank/motion_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = kwargs.get('slug')
        try:
            motion = MotionEntry.objects.select_related('analysis', 'stats').get(slug=slug)
            context['motion'] = motion
            context['page_title'] = motion.text[:80]
            context['page_emoji'] = '🎯'

            # SEO: structured data for motion page
            context['canonical_url'] = self.request.build_absolute_uri()
            context['seo_keywords'] = ', '.join(motion.theme_tags) if motion.theme_tags else 'debate motion'
        except MotionEntry.DoesNotExist:
            context['page_title'] = 'Motion Not Found'
        return context


class MotionDoctorView(TemplateView):
    template_name = 'motionbank/motion_doctor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Motion Doctor'
        context['page_emoji'] = '🩺'
        return context


class MotionSubmitView(LoginRequiredMixin, TemplateView):
    template_name = 'motionbank/motion_submit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Submit a Motion'
        context['page_emoji'] = '📝'
        return context


# =============================================================================
# API Views
# =============================================================================

class MotionEntryListAPI(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['text', 'tournament_name', 'region']
    ordering_fields = ['created_at', 'year', 'difficulty']
    ordering = ['-year', '-created_at']

    def get_queryset(self):
        qs = MotionEntry.objects.filter(is_approved=True).select_related('stats', 'analysis')

        # Multi-filter support
        fmt = self.request.query_params.get('debate_format')
        if fmt:
            qs = qs.filter(format=fmt)

        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(year=year)

        region = self.request.query_params.get('region')
        if region:
            qs = qs.filter(region__icontains=region)

        tournament = self.request.query_params.get('tournament')
        if tournament:
            qs = qs.filter(tournament_name__icontains=tournament)

        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        motion_type = self.request.query_params.get('type')
        if motion_type:
            qs = qs.filter(motion_type=motion_type)

        prep = self.request.query_params.get('prep')
        if prep:
            qs = qs.filter(prep_type=prep)

        theme = self.request.query_params.get('theme')
        if theme:
            qs = qs.filter(theme_tags__contains=[theme])

        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MotionEntryCreateSerializer
        return MotionEntryListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class MotionEntryDetailAPI(generics.RetrieveAPIView):
    queryset = MotionEntry.objects.filter(is_approved=True).select_related(
        'analysis', 'stats',
    ).prefetch_related('case_outlines__author', 'ratings')
    serializer_class = MotionEntryDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]


class MotionRateAPI(generics.CreateAPIView):
    serializer_class = MotionRatingSerializer
    permission_classes = [permissions.IsAuthenticated]


class CaseOutlineListAPI(generics.ListCreateAPIView):
    serializer_class = CaseOutlineSerializer

    def get_queryset(self):
        motion_id = self.kwargs.get('motion_id')
        qs = CaseOutline.objects.filter(motion_id=motion_id)
        side = self.request.query_params.get('side')
        if side:
            qs = qs.filter(side=side)
        return qs

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CaseOutlineVoteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outline_id):
        from django.db import transaction
        outline = get_object_or_404(CaseOutline, pk=outline_id)
        with transaction.atomic():
            outline = CaseOutline.objects.select_for_update().get(pk=outline_id)
            vote, created = CaseOutlineVote.objects.get_or_create(
                user=request.user, case_outline=outline,
            )
            if created:
                outline.upvotes = F('upvotes') + 1
                outline.save(update_fields=['upvotes'])
                outline.refresh_from_db()
                return Response({'upvotes': outline.upvotes}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Already voted'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, outline_id):
        from django.db import transaction
        outline = get_object_or_404(CaseOutline, pk=outline_id)
        with transaction.atomic():
            outline = CaseOutline.objects.select_for_update().get(pk=outline_id)
            deleted, _ = CaseOutlineVote.objects.filter(
                user=request.user, case_outline=outline,
            ).delete()
            if deleted and outline.upvotes > 0:
                outline.upvotes = F('upvotes') - 1
                outline.save(update_fields=['upvotes'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MotionDoctorAnalyzeAPI(APIView):
    """AI-powered motion analysis endpoint — the Motion Doctor.

    Pipeline: Profiler → Planner → Generator → Validator
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MotionDoctorInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        motion_text = serializer.validated_data['motion_text']
        debate_format = serializer.validated_data.get('format', 'bp')
        info_slide = serializer.validated_data.get('info_slide', '')
        level = serializer.validated_data.get('level', 'open')

        # Check for cached report (exact match)
        existing_report = MotionReport.objects.filter(
            motion_text__iexact=motion_text,
            format=debate_format,
        ).order_by('-created_at').first()

        if existing_report and existing_report.report_json:
            return Response({
                'report_id': str(existing_report.id),
                'motion_text': motion_text,
                'report': existing_report.report_json,
                'profile': existing_report.profile_json,
                'plan': existing_report.plan_json,
                'validation_log': existing_report.validation_log,
                'model_version': existing_report.model_version,
                'cached': True,
            })

        # Run the 4-prompt pipeline
        from .prompts import MotionDoctorPipeline

        pipeline = MotionDoctorPipeline()

        # Retrieve archetypes (simple keyword match for now; embeddings later)
        archetypes = self._get_matching_archetypes(motion_text)
        similar_motions = self._get_similar_motions(motion_text)

        report, metadata = pipeline.run(
            motion_text=motion_text,
            debate_format=debate_format,
            info_slide=info_slide,
            archetypes=archetypes,
            similar_motions=similar_motions,
        )

        # Persist the report
        motion_entry = MotionEntry.objects.filter(text__iexact=motion_text).first()
        saved_report = MotionReport.objects.create(
            motion=motion_entry,
            motion_text=motion_text,
            info_slide=info_slide,
            format=debate_format,
            report_json=report,
            profile_json=metadata.get('profile', {}),
            plan_json=metadata.get('plan', {}),
            validation_log=metadata.get('validation_issues', []),
            model_version=metadata.get('model_version', 'fallback'),
            pipeline_duration_ms=metadata.get('pipeline_duration_ms'),
        )

        return Response({
            'report_id': str(saved_report.id),
            'motion_text': motion_text,
            'report': report,
            'profile': metadata.get('profile', {}),
            'plan': metadata.get('plan', {}),
            'validation_log': metadata.get('validation_issues', []),
            'model_version': metadata.get('model_version', 'fallback'),
            'pipeline_stages': metadata.get('stages', {}),
            'pipeline_duration_ms': metadata.get('pipeline_duration_ms'),
            'cached': False,
        })

    def _get_matching_archetypes(self, motion_text):
        """Retrieve matching archetypes via keyword overlap."""
        text_lower = motion_text.lower()
        results = []
        for arch in Archetype.objects.all()[:50]:
            triggers = arch.trigger_features
            if isinstance(triggers, dict):
                keywords = triggers.get('keywords', [])
                if any(kw.lower() in text_lower for kw in keywords):
                    results.append({
                        'name': arch.name,
                        'domain_tags': arch.domain_tags,
                        'canonical_clashes': arch.canonical_clashes,
                        'canonical_stakeholders': arch.canonical_stakeholders,
                        'gov_playbook': arch.gov_playbook,
                        'opp_playbook': arch.opp_playbook,
                        'definition_traps': arch.definition_traps,
                        'weighing_tools': arch.weighing_tools,
                    })
        return results[:5]

    def _get_similar_motions(self, motion_text):
        """Retrieve similar motion texts via simple text search."""
        keywords = [w for w in motion_text.split() if len(w) > 4][:5]
        if not keywords:
            return []
        q = Q()
        for kw in keywords:
            q |= Q(text__icontains=kw)
        similar = MotionEntry.objects.filter(q, is_approved=True).exclude(
            text__iexact=motion_text,
        ).values_list('text', flat=True)[:10]
        return list(similar)


class MotionReportFeedbackAPI(generics.CreateAPIView):
    """Submit feedback on a Motion Doctor report."""
    serializer_class = MotionReportFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PracticeSessionAPI(generics.ListCreateAPIView):
    serializer_class = PracticeSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PracticeSession.objects.filter(user=self.request.user)


class MotionFiltersAPI(APIView):
    """Returns available filter options for the motion bank."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        motions = MotionEntry.objects.filter(is_approved=True)

        formats = list(motions.values_list('format', flat=True).distinct())
        years = sorted(
            motions.exclude(year__isnull=True).values_list('year', flat=True).distinct(),
            reverse=True,
        )
        regions = sorted(motions.exclude(region='').values_list('region', flat=True).distinct())
        tournaments = sorted(motions.exclude(tournament_name='').values_list('tournament_name', flat=True).distinct())

        # Collect all unique theme tags
        themes = set()
        for tags in motions.values_list('theme_tags', flat=True):
            if tags:
                themes.update(tags)

        return Response({
            'formats': [{'value': f, 'label': dict(MotionEntry.MotionFormat.choices).get(f, f)} for f in formats],
            'years': [y for y in years if y],
            'regions': regions,
            'tournaments': tournaments,
            'themes': sorted(themes),
            'difficulties': [{'value': c[0], 'label': c[1]} for c in MotionEntry.Difficulty.choices],
            'motion_types': [{'value': c[0], 'label': c[1]} for c in MotionEntry.MotionType.choices],
            'prep_types': [{'value': c[0], 'label': c[1]} for c in MotionEntry.PrepType.choices],
        })
