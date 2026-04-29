import json
import logging
import os
import time

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from rest_framework import generics, permissions, status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MotionEntry, MotionRating, CaseOutline, CaseOutlineVote, PracticeSession,
)
from .serializers import (
    MotionEntryListSerializer, MotionEntryDetailSerializer,
    MotionEntryCreateSerializer,
    MotionRatingSerializer, CaseOutlineSerializer,
    PracticeSessionSerializer,
)

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


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
    pagination_class = StandardPagination
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
        with transaction.atomic():
            try:
                outline = CaseOutline.objects.select_for_update().get(pk=outline_id)
            except CaseOutline.DoesNotExist:
                return Response({'detail': 'Outline not found'}, status=status.HTTP_404_NOT_FOUND)
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
        with transaction.atomic():
            try:
                outline = CaseOutline.objects.select_for_update().get(pk=outline_id)
            except CaseOutline.DoesNotExist:
                return Response({'detail': 'Outline not found'}, status=status.HTTP_404_NOT_FOUND)
            deleted, _ = CaseOutlineVote.objects.filter(
                user=request.user, case_outline=outline,
            ).delete()
            if deleted and outline.upvotes > 0:
                outline.upvotes = F('upvotes') - 1
                outline.save(update_fields=['upvotes'])
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'No vote to remove'}, status=status.HTTP_404_NOT_FOUND)


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

        # Collect all unique theme tags (skip empty)
        themes = set()
        for tags in motions.exclude(theme_tags=[]).values_list('theme_tags', flat=True):
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


# =============================================================================
# /motions/ — Flat-file Motion Bank (served from Motion-Bank JSON)
# =============================================================================

_MOTIONS_CACHE = {'data': None}


def _get_motions_data():
    """Load and cache the Motion-Bank JSON. Thread-safe for read-only after first load."""
    if _MOTIONS_CACHE['data'] is None:
        path = os.path.join(
            os.path.dirname(settings.BASE_DIR),
            'Motion-Bank',
            'motions-version-01.json',
        )
        with open(path, encoding='utf-8') as f:
            _MOTIONS_CACHE['data'] = json.load(f)
        logger.info("Motion-Bank JSON loaded: %d records", len(_MOTIONS_CACHE['data']))
    return _MOTIONS_CACHE['data']


class MotionsPageView(TemplateView):
    """Renders the /motions/ shell page. Actual data is fetched by JS via MotionsAPIView."""
    template_name = 'motionbank/motions_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['motion_types'] = ['THBT', 'THO', 'THP', 'THR', 'THS', 'THW']
        context['styles'] = [
            'BP', 'World Schools', 'Asians/Australs', 'Public Forum',
            'Lincoln-Douglas', 'Policy', 'CNDF', 'CP',
        ]
        context['levels'] = ['University', 'School', 'Mixed']
        context['regions'] = [
            'Africa', 'Asia', 'Europe', 'Latin America',
            'Middle East', 'North America', 'Oceania', 'South America',
        ]
        context['categories'] = [
            'Politics', 'Economics', 'Law', 'Social Justice', 'Culture',
            'International Relations', 'Media', 'Science/Technology',
            'Education/Academia', 'Criminal Justice', 'Medical', 'Military',
            'Children', 'Religion', 'Philosophy', 'Feminism',
            'Romance/Sexuality', 'Environment', 'Development',
            'Minority Communities', 'Sports', 'LGBTQ+', 'Art',
        ]
        return context


class MotionsAPIView(View):
    """Paginated, filtered JSON API backed by the flat Motion-Bank JSON file."""

    # Normalise messy style values → canonical display names
    _STYLE_MAP = {
        ' bp': 'BP', 'bp': 'BP',
        'asians/australa': 'Asians/Australs',
        'asians/australs': 'Asians/Australs',
        'australs/asians': 'Asians/Australs',
        'australs': 'Asians/Australs',
        'world schools': 'World Schools',
        'public forum': 'Public Forum',
        'lincoln-douglas': 'Lincoln-Douglas',
        'policy': 'Policy', 'cndf': 'CNDF', 'cp': 'CP',
        'university': 'University',
    }

    # Normalise messy level values → canonical
    _LEVEL_MAP = {
        'university': 'University', 'unversity': 'University',
        'bp': 'University', 'school': 'School', 'schools': 'School',
        'mixed': 'Mixed',
    }

    # Normalise messy region values → canonical
    _REGION_MAP = {
        'asian': 'Asia',
        'north american': 'North America',
        'pakistan': 'Asia',
    }

    def _norm_style(self, raw):
        return self._STYLE_MAP.get((raw or '').lower().strip(), (raw or '').strip())

    def _norm_level(self, raw):
        return self._LEVEL_MAP.get((raw or '').lower().strip(), (raw or '').strip())

    def _norm_region(self, raw):
        return self._REGION_MAP.get((raw or '').lower().strip(), (raw or '').strip())

    def get(self, request):
        data = _get_motions_data()

        q            = (request.GET.get('q') or '').strip().lower()
        style        = (request.GET.get('style') or '').strip()
        level        = (request.GET.get('level') or '').strip()
        region       = (request.GET.get('region') or '').strip()
        motion_type  = (request.GET.get('motion_type') or '').strip()
        category     = (request.GET.get('category') or '').strip()
        year_from    = (request.GET.get('year_from') or '').strip()
        year_to      = (request.GET.get('year_to') or '').strip()
        sort         = (request.GET.get('sort') or 'date_desc').strip()

        try:
            page = max(1, int(request.GET.get('page') or 1))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(max(1, int(request.GET.get('page_size') or 25)), 100)
        except (ValueError, TypeError):
            page_size = 25

        results = data

        if q:
            results = [
                m for m in results
                if q in (m.get('motion') or '').lower()
                or q in (m.get('infoslide') or '').lower()
                or q in (m.get('tournament_name') or '').lower()
            ]

        if style:
            results = [m for m in results if self._norm_style(m.get('style')) == style]

        if level:
            results = [m for m in results if self._norm_level(m.get('level')) == level]

        if region:
            # Build the set of raw values that map to the requested canonical region
            target_raws = {
                raw for raw, canon in self._REGION_MAP.items() if canon == region
            }
            target_raws.add(region)
            results = [m for m in results if (m.get('region') or '') in target_raws]

        if motion_type:
            results = [m for m in results if (m.get('motion_type') or '') == motion_type]

        if category:
            results = [
                m for m in results
                if category in (m.get('primary_types') or [])
                or category in (m.get('secondary_types') or [])
            ]

        if year_from:
            results = [m for m in results if (m.get('start_date') or '0000')[:4] >= year_from]
        if year_to:
            results = [m for m in results if (m.get('start_date') or '9999')[:4] <= year_to]

        # Sorting
        if sort == 'date_desc':
            results = sorted(results, key=lambda m: m.get('start_date') or '', reverse=True)
        elif sort == 'date_asc':
            results = sorted(results, key=lambda m: m.get('start_date') or '')
        elif sort == 'difficulty_desc':
            results = sorted(results, key=lambda m: m.get('difficulty_complexity') or 0, reverse=True)
        elif sort == 'difficulty_asc':
            results = sorted(results, key=lambda m: m.get('difficulty_complexity') or 0)

        total = len(results)
        start = (page - 1) * page_size
        page_results = results[start:start + page_size]

        slim = [{
            'id':                   m.get('id'),
            'motion':               m.get('motion') or '',
            'infoslide':            m.get('infoslide') or '',
            'motion_type':          m.get('motion_type') or '',
            'tournament_name':      m.get('tournament_name') or '',
            'round':                m.get('round') or '',
            'start_date':           (m.get('start_date') or '')[:10],
            'region':               m.get('region') or '',
            'country':              m.get('country') or '',
            'city':                 m.get('city') or '',
            'level':                m.get('level') or '',
            'style':                m.get('style') or '',
            'primary_types':        m.get('primary_types') or [],
            'secondary_types':      m.get('secondary_types') or [],
            'bias_burden_pro':      m.get('bias_burden_pro'),
            'bias_burden_opp':      m.get('bias_burden_opp'),
            'difficulty_technical': m.get('difficulty_technical'),
            'difficulty_complexity':m.get('difficulty_complexity'),
            'difficulty_abstraction':m.get('difficulty_abstraction'),
            'difficulty_depth':     m.get('difficulty_depth'),
            'tab_url':              m.get('tab_url') or '',
            'adjudicators':         m.get('adjudicators') or [],
        } for m in page_results]

        return JsonResponse({
            'results': slim,
            'total':   total,
            'page':    page,
            'page_size': page_size,
            'pages':   (total + page_size - 1) // page_size,
        })
