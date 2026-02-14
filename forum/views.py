from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
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
# API Views
# =============================================================================

class ForumTagListAPI(generics.ListAPIView):
    queryset = ForumTag.objects.all()
    serializer_class = ForumTagSerializer
    permission_classes = [permissions.AllowAny]


class ForumThreadListAPI(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'tags__name']
    ordering_fields = ['created_at', 'updated_at', 'view_count']
    ordering = ['-is_pinned', '-updated_at']

    def get_queryset(self):
        qs = ForumThread.objects.annotate(
            _reply_count=Count('posts'),
        ).select_related('author', 'linked_motion').prefetch_related('tags', 'author__forum_badges')

        # Filters
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
    queryset = ForumThread.objects.annotate(
        _reply_count=Count('posts'),
    ).select_related('author', 'linked_motion').prefetch_related(
        'tags', 'posts__author', 'posts__children', 'posts__votes', 'author__forum_badges',
    )
    serializer_class = ForumThreadDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count atomically to prevent race conditions
        ForumThread.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ForumPostCreateAPI(generics.CreateAPIView):
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ForumPostUpdateAPI(generics.UpdateAPIView):
    queryset = ForumPost.objects.all()
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        # Only allow editing content, not moving posts between threads
        kwargs['partial'] = True
        serializer = super().get_serializer(*args, **kwargs)
        return serializer

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own posts.")
        # Only save content changes, ignore thread/parent
        serializer.save(is_edited=True, thread=serializer.instance.thread, parent=serializer.instance.parent)


class ForumVoteAPI(generics.CreateAPIView):
    """Create or update a vote with explicit user handling."""
    serializer_class = ForumVoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ForumVoteDeleteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, post_id):
        ForumVote.objects.filter(user=request.user, post_id=post_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'Thread already bookmarked.'})
        # Set instance so DRF can serialize the response
        serializer.instance = bookmark


class ForumBookmarkDeleteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, thread_id):
        ForumBookmark.objects.filter(user=request.user, thread_id=thread_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForumReportCreateAPI(generics.CreateAPIView):
    serializer_class = ForumReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class UserBadgeListAPI(generics.ListAPIView):
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return UserBadge.objects.filter(user_id=user_id, verified=True)
