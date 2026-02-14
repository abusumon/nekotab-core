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
)
from .serializers import (
    MotionEntryListSerializer, MotionEntryDetailSerializer,
    MotionEntryCreateSerializer, MotionAnalysisSerializer,
    MotionRatingSerializer, CaseOutlineSerializer,
    MotionDoctorInputSerializer, PracticeSessionSerializer,
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
        fmt = self.request.query_params.get('format')
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
        outline = get_object_or_404(CaseOutline, pk=outline_id)
        vote, created = CaseOutlineVote.objects.get_or_create(
            user=request.user, case_outline=outline,
        )
        if created:
            CaseOutline.objects.filter(pk=outline.pk).update(upvotes=F('upvotes') + 1)
            outline.refresh_from_db()
            return Response({'upvotes': outline.upvotes}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Already voted'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, outline_id):
        outline = get_object_or_404(CaseOutline, pk=outline_id)
        deleted, _ = CaseOutlineVote.objects.filter(
            user=request.user, case_outline=outline,
        ).delete()
        if deleted:
            CaseOutline.objects.filter(pk=outline.pk, upvotes__gt=0).update(upvotes=F('upvotes') - 1)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MotionDoctorAnalyzeAPI(APIView):
    """AI-powered motion analysis endpoint — the Motion Doctor."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MotionDoctorInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        motion_text = serializer.validated_data['motion_text']
        debate_format = serializer.validated_data.get('format', 'bp')
        info_slide = serializer.validated_data.get('info_slide', '')

        # Check if this motion already has an analysis
        existing = MotionEntry.objects.filter(text__iexact=motion_text).first()
        if existing and hasattr(existing, 'analysis'):
            return Response({
                'motion_id': existing.id,
                'analysis': MotionAnalysisSerializer(existing.analysis).data,
                'cached': True,
            })

        # Generate AI analysis
        analysis = self._generate_analysis(motion_text, debate_format, info_slide)

        return Response({
            'motion_text': motion_text,
            'analysis': analysis,
            'cached': False,
        })

    def _generate_analysis(self, motion_text, debate_format, info_slide=''):
        """Generate structured motion analysis.

        This is a template-based fallback. In production, this would call
        an AI service (OpenAI, Claude, etc.) for intelligent analysis.
        """
        # Determine motion type from prefix
        text_lower = motion_text.lower().strip()
        if text_lower.startswith('thw ') or text_lower.startswith('this house would'):
            motion_type = 'THW (Policy-leaning)'
        elif text_lower.startswith('thbt ') or text_lower.startswith('this house believes that'):
            motion_type = 'THBT (Value-leaning)'
        elif text_lower.startswith('thr ') or text_lower.startswith('this house regrets'):
            motion_type = 'THR (Evaluative)'
        elif text_lower.startswith('ths ') or text_lower.startswith('this house supports'):
            motion_type = 'THS (Stance)'
        else:
            motion_type = 'General'

        format_name = dict(MotionEntry.MotionFormat.choices).get(debate_format, 'British Parliamentary')

        analysis = {
            'motion_type_detected': motion_type,
            'format': str(format_name),
            'hidden_assumptions': [
                f"The motion assumes a specific actor or mechanism is available",
                f"There may be an implicit status quo being challenged",
                f"The scope of '{motion_text[:50]}...' needs clear definition",
            ],
            'model_problems': [
                "Defining the exact mechanism or policy change required",
                "Establishing who the relevant stakeholders are",
                "Determining the appropriate timeframe for evaluation",
            ],
            'clash_areas': [
                "Principled vs. pragmatic evaluation",
                "Rights of individuals vs. collective welfare",
                "Short-term consequences vs. long-term systemic change",
                "Status quo defense vs. burden of proof on change",
            ],
            'framing_mistakes': [
                "Over-narrowing the definition to avoid clash",
                "Failing to establish clear metrics for success",
                "Ignoring the strongest opposition arguments in framing",
            ],
            'gov_approach': {
                'structure': f"For {format_name}: Clear mechanism → stakeholder impact → principled justification",
                'key_args': [
                    "Establish clear harm in status quo",
                    "Present actionable mechanism",
                    "Show net benefit across stakeholders",
                ],
            },
            'opp_approach': {
                'structure': "Challenge mechanism feasibility → show unintended consequences → defend status quo value",
                'key_args': [
                    "Attack the feasibility or desirability of the change",
                    "Present stronger counter-mechanisms",
                    "Show that the costs outweigh the benefits",
                ],
            },
            'definition_traps': [
                "Avoid overly specific geographic or temporal definitions",
                "Don't define away the opposition's ground",
                "Ensure definitions are fair, clear, and debatable",
            ],
            'burden_split': (
                "Gov must prove that the proposed change is desirable and feasible. "
                "Opp must either defend the status quo or present a superior alternative."
            ),
            'likely_extensions': {
                'CG': "Deeper principled analysis or new stakeholder group",
                'CO': "Systemic critique or long-term consequences",
            },
            'weighing_options': [
                "Scope of impact (how many people affected)",
                "Severity of harm/benefit",
                "Likelihood of the scenario occurring",
                "Reversibility of consequences",
            ],
            'suggested_pois': [
                f"Can you clarify your exact mechanism for implementing this?",
                f"What happens to [affected group] under your model?",
                f"How do you account for the unintended consequences of [X]?",
                f"Where is your principled line for when this applies?",
                f"Isn't this exactly what happens in [counter-example country]?",
                f"How do you weigh [value A] against [value B]?",
                f"What's the counterfactual — what happens if we don't do this?",
                f"How do you respond to [strongest opp/gov argument]?",
                f"Are you assuming perfect implementation?",
                f"What empirical evidence supports your causal chain?",
            ],
            'difficulty_estimate': 3,
            'difficulty_rationale': 'Moderate complexity — requires balanced analysis of competing values',
        }

        # Try to call AI service if available
        ai_api_key = environ.get('OPENAI_API_KEY') or environ.get('ANTHROPIC_API_KEY')
        if ai_api_key:
            try:
                analysis = self._call_ai_service(motion_text, debate_format, info_slide, ai_api_key)
            except Exception as e:
                logger.warning(f"AI analysis failed, using template: {e}")

        return analysis

    def _call_ai_service(self, motion_text, debate_format, info_slide, api_key):
        """Call external AI API for intelligent motion analysis.

        Override this method to integrate with OpenAI, Anthropic, or other AI services.
        """
        # Placeholder for AI integration
        # In production, this would make an API call to generate analysis
        raise NotImplementedError("AI service integration not yet configured")


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
