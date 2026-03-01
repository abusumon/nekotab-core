import math
from datetime import timezone as tz

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Max, Q, Sum, Case, When, IntegerField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from rest_framework import generics, permissions, status, filters
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import (
    ForumTag, UserBadge, ForumThread, ForumPost,
    ForumVote, ForumBookmark, ForumReport,
)
from .serializers import (
    ForumTagSerializer, UserBadgeSerializer,
    ForumThreadListSerializer, ForumThreadDetailSerializer,
    ForumThreadCreateSerializer, ForumPostSerializer,
    ForumVoteSerializer, ForumBookmarkSerializer, ForumReportSerializer,
)


# =============================================================================
# Permissions
# =============================================================================

class IsAuthorOrStaff(permissions.BasePermission):
    """Allow if user is the author OR is_staff (moderator)."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        author = getattr(obj, 'author', None)
        return author == request.user


class IsStaff(permissions.BasePermission):
    """Allow only staff/moderators."""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


# =============================================================================
# Rate Throttles
# =============================================================================

class PostCreateThrottle(UserRateThrottle):
    rate = '10/min'
    scope = 'forum_post'


class VoteThrottle(UserRateThrottle):
    rate = '60/min'
    scope = 'forum_vote'


# =============================================================================
# Template Views (Page Shells)
# =============================================================================

class ForumHomeView(TemplateView):
    template_name = 'forum/forum_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Global Debate Forum'
        context['page_emoji'] = '💬'
        return context


class ForumThreadView(TemplateView):
    template_name = 'forum/forum_thread.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['thread_slug'] = kwargs.get('slug')
        context['page_title'] = 'Discussion'
        context['page_emoji'] = '🗣️'
        return context


class ForumCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'forum/forum_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'New Discussion'
        context['page_emoji'] = '✏️'
        return context


# =============================================================================
# API Views — Tags
# =============================================================================

class ForumTagListAPI(generics.ListAPIView):
    queryset = ForumTag.objects.all()
    serializer_class = ForumTagSerializer
    permission_classes = [permissions.AllowAny]


# =============================================================================
# API Views — Threads (with Hot / New / Top sorting)
# =============================================================================

class ForumThreadListAPI(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'tags__name']
    ordering_fields = ['created_at', 'updated_at', 'view_count', 'score']
    ordering = ['-is_pinned', '-updated_at']

    def get_queryset(self):
        qs = ForumThread.objects.filter(is_deleted=False).annotate(
            _reply_count=Count('posts', filter=Q(posts__is_deleted=False)),
            _last_activity=Coalesce(
                Max('posts__created_at', filter=Q(posts__is_deleted=False)),
                F('created_at'),
            ),
            _score_ann=Coalesce(
                Sum(
                    Case(
                        When(posts__votes__vote_type='up', then=Value(1)),
                        When(posts__votes__vote_type='down', then=Value(-1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                    filter=Q(posts__parent__isnull=True, posts__is_deleted=False),
                ),
                Value(0),
            ),
        ).select_related('author', 'linked_motion').prefetch_related(
            'tags', 'author__forum_badges',
        )

        # ── Sorting: hot / new / top ──
        sort = self.request.query_params.get('sort', '').lower()
        if sort == 'new':
            qs = qs.order_by('-is_pinned', '-created_at')
        elif sort == 'top':
            qs = qs.order_by('-is_pinned', '-_score_ann', '-created_at')
        elif sort == 'hot':
            qs = qs.order_by('-is_pinned', '-_score_ann', '-_last_activity')
        # else: default ordering (pinned → updated)

        # ── Filters ──
        fmt = self.request.query_params.get('format')
        if fmt:
            qs = qs.filter(debate_format=fmt)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(topic_category=category)

        skill = self.request.query_params.get('skill')
        if skill:
            qs = qs.filter(skill_level=skill)

        region = self.request.query_params.get('region')
        if region:
            qs = qs.filter(region__icontains=region)

        tag = self.request.query_params.get('tag')
        if tag:
            qs = qs.filter(tags__slug=tag)

        motion_id = self.request.query_params.get('motion')
        if motion_id:
            qs = qs.filter(linked_motion_id=motion_id)

        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ForumThreadCreateSerializer
        return ForumThreadListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class ForumThreadDetailAPI(generics.RetrieveAPIView):
    serializer_class = ForumThreadDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return ForumThread.objects.filter(is_deleted=False).annotate(
            _reply_count=Count('posts', filter=Q(posts__is_deleted=False)),
            _last_activity=Coalesce(
                Max('posts__created_at', filter=Q(posts__is_deleted=False)),
                F('created_at'),
            ),
        ).select_related('author', 'linked_motion').prefetch_related(
            'tags', 'posts__author', 'posts__children', 'posts__votes',
            'author__forum_badges',
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        ForumThread.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ForumThreadDeleteAPI(APIView):
    """Soft-delete a thread (author or staff)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        thread = get_object_or_404(ForumThread, slug=slug, is_deleted=False)
        if not (request.user.is_staff or thread.author == request.user):
            raise PermissionDenied("You can only delete your own threads.")
        ForumThread.objects.filter(pk=thread.pk).update(is_deleted=True)
        return Response({'detail': 'Thread deleted.'}, status=status.HTTP_200_OK)


class ForumThreadLockAPI(APIView):
    """Lock a thread (staff only)."""
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def post(self, request, slug):
        thread = get_object_or_404(ForumThread, slug=slug, is_deleted=False)
        ForumThread.objects.filter(pk=thread.pk).update(is_locked=True)
        return Response({'detail': 'Thread locked.'})


class ForumThreadUnlockAPI(APIView):
    """Unlock a thread (staff only)."""
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def post(self, request, slug):
        thread = get_object_or_404(ForumThread, slug=slug, is_deleted=False)
        ForumThread.objects.filter(pk=thread.pk).update(is_locked=False)
        return Response({'detail': 'Thread unlocked.'})


# =============================================================================
# API Views — Posts (Comments)
# =============================================================================

class ForumPostCreateAPI(generics.CreateAPIView):
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PostCreateThrottle]

    def perform_create(self, serializer):
        thread = serializer.validated_data.get('thread')
        if thread and thread.is_locked:
            raise PermissionDenied("This thread is locked. No new replies are allowed.")
        post = serializer.save(author=self.request.user)
        # Update cached comment_count on thread
        ForumThread.objects.filter(pk=post.thread_id).update(
            comment_count=F('comment_count') + 1,
        )


class ForumPostUpdateAPI(generics.UpdateAPIView):
    queryset = ForumPost.objects.filter(is_deleted=False).select_related('author').prefetch_related('votes', 'children')
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        kwargs['partial'] = True
        serializer = super().get_serializer(*args, **kwargs)
        return serializer

    def perform_update(self, serializer):
        if not (self.request.user.is_staff or serializer.instance.author == self.request.user):
            raise PermissionDenied("You can only edit your own posts.")
        serializer.save(
            is_edited=True,
            thread=serializer.instance.thread,
            parent=serializer.instance.parent,
        )


class ForumPostDeleteAPI(APIView):
    """Soft-delete a post (author or staff)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
        if not (request.user.is_staff or post.author == request.user):
            raise PermissionDenied("You can only delete your own posts.")
        ForumPost.objects.filter(pk=post.pk).update(is_deleted=True)
        # Decrement cached comment_count
        ForumThread.objects.filter(pk=post.thread_id).update(
            comment_count=Case(
                When(comment_count__gt=0, then=F('comment_count') - 1),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        return Response({'detail': 'Post deleted.'}, status=status.HTTP_200_OK)


# =============================================================================
# API Views — Votes
# =============================================================================

class ForumVoteAPI(generics.CreateAPIView):
    """Create, update, or remove a vote."""
    serializer_class = ForumVoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [VoteThrottle]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ForumVoteDeleteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, post_id):
        deleted_count, _ = ForumVote.objects.filter(user=request.user, post_id=post_id).delete()
        if deleted_count:
            try:
                post = ForumPost.objects.get(pk=post_id)
                post.refresh_score()
            except ForumPost.DoesNotExist:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# API Views — Bookmarks
# =============================================================================

class ForumBookmarkListAPI(generics.ListCreateAPIView):
    serializer_class = ForumBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ForumBookmark.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        thread = serializer.validated_data['thread']
        bookmark, created = ForumBookmark.objects.get_or_create(
            user=self.request.user, thread=thread,
        )
        if not created:
            raise ValidationError({'detail': 'Thread already bookmarked.'})
        serializer.instance = bookmark


class ForumBookmarkDeleteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, thread_id):
        ForumBookmark.objects.filter(user=request.user, thread_id=thread_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# API Views — Reports
# =============================================================================

class ForumReportCreateAPI(generics.CreateAPIView):
    serializer_class = ForumReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ForumReportListAPI(generics.ListAPIView):
    """List unresolved reports (staff/mod only)."""
    serializer_class = ForumReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def get_queryset(self):
        qs = ForumReport.objects.select_related('reporter', 'post__thread', 'post__author')
        if self.request.query_params.get('all') != '1':
            qs = qs.filter(resolved=False)
        return qs


class ForumReportResolveAPI(APIView):
    """Mark a report as resolved (staff/mod only)."""
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def post(self, request, pk):
        report = get_object_or_404(ForumReport, pk=pk)
        report.resolved = True
        report.save(update_fields=['resolved'])
        return Response({'detail': 'Report resolved.'})


# =============================================================================
# API Views — Badges
# =============================================================================

class UserBadgeListAPI(generics.ListAPIView):
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return UserBadge.objects.filter(user_id=user_id, verified=True)
