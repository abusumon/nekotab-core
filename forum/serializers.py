from rest_framework import serializers
from .models import (
    ForumTag, UserBadge, ForumThread, ForumPost,
    ForumVote, ForumBookmark, ForumReport,
)


class ForumTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumTag
        fields = ['id', 'name', 'slug', 'color', 'description']


class UserBadgeSerializer(serializers.ModelSerializer):
    badge_type_display = serializers.CharField(source='get_badge_type_display', read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'user', 'badge_type', 'badge_type_display', 'verified', 'awarded_at']
        read_only_fields = ['verified', 'verified_by', 'awarded_at']


class ForumPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_badges = UserBadgeSerializer(source='author.forum_badges', many=True, read_only=True)
    post_type_display = serializers.CharField(source='get_post_type_display', read_only=True)
    vote_score = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()

    class Meta:
        model = ForumPost
        fields = [
            'id', 'thread', 'author', 'author_name', 'author_badges',
            'parent', 'post_type', 'post_type_display', 'content',
            'is_edited', 'is_deleted', 'score', 'vote_score', 'user_vote',
            'depth', 'children',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['author', 'is_edited', 'is_deleted', 'score', 'created_at', 'updated_at']

    def get_children(self, obj):
        children = [c for c in obj.children.all() if not c.is_deleted]
        return ForumPostSerializer(children, many=True, context=self.context).data

    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            for vote in obj.votes.all():
                if vote.user_id == request.user.id:
                    return vote.vote_type
        return None

    def get_depth(self, obj):
        """Compute depth from parent chain (capped at 10 for safety)."""
        depth = 0
        current = obj
        seen = set()
        while current.parent_id is not None and depth < 10:
            if current.pk in seen:
                break
            seen.add(current.pk)
            depth += 1
            # Use prefetch cache if available
            try:
                current = current.parent
            except Exception:
                break
        return depth


class ForumThreadListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_badges = UserBadgeSerializer(source='author.forum_badges', many=True, read_only=True)
    tags = ForumTagSerializer(many=True, read_only=True)
    reply_count = serializers.IntegerField(source='_reply_count', read_only=True, default=0)
    last_activity = serializers.DateTimeField(read_only=True)
    format_display = serializers.CharField(source='get_debate_format_display', read_only=True)
    category_display = serializers.CharField(source='get_topic_category_display', read_only=True)
    skill_display = serializers.CharField(source='get_skill_level_display', read_only=True)

    class Meta:
        model = ForumThread
        fields = [
            'id', 'title', 'slug', 'author', 'author_name', 'author_badges',
            'debate_format', 'format_display',
            'topic_category', 'category_display',
            'skill_level', 'skill_display',
            'region', 'tags', 'linked_motion',
            'is_pinned', 'is_locked', 'view_count', 'score', 'comment_count',
            'reply_count', 'last_activity',
            'created_at', 'updated_at',
        ]


class ForumThreadDetailSerializer(ForumThreadListSerializer):
    posts = serializers.SerializerMethodField()

    class Meta(ForumThreadListSerializer.Meta):
        fields = ForumThreadListSerializer.Meta.fields + ['posts']

    def get_posts(self, obj):
        # Only root posts that are NOT soft-deleted
        root_posts = [p for p in obj.posts.all() if p.parent_id is None and not p.is_deleted]
        # Sort by request param
        request = self.context.get('request')
        comment_sort = request.query_params.get('comment_sort', 'top') if request else 'top'
        if comment_sort == 'new':
            root_posts.sort(key=lambda p: p.created_at, reverse=True)
        else:  # 'top' default
            root_posts.sort(key=lambda p: p.vote_score, reverse=True)
        return ForumPostSerializer(root_posts, many=True, context=self.context).data


class ForumThreadCreateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ForumTag.objects.all(),
        write_only=True, required=False, source='tags',
    )
    initial_post = serializers.CharField(write_only=True)

    class Meta:
        model = ForumThread
        fields = [
            'id', 'title', 'slug', 'debate_format', 'topic_category', 'skill_level',
            'region', 'tag_ids', 'initial_post', 'linked_motion',
        ]
        read_only_fields = ['id', 'slug']

    def create(self, validated_data):
        initial_post_content = validated_data.pop('initial_post')
        tags = validated_data.pop('tags', [])
        author = self.context['request'].user

        from django.utils.text import slugify
        import uuid
        base_slug = slugify(validated_data['title'])[:300]
        validated_data['slug'] = f"{base_slug}-{uuid.uuid4().hex[:8]}"

        thread = ForumThread.objects.create(author=author, **validated_data)
        thread.tags.set(tags)

        ForumPost.objects.create(
            thread=thread,
            author=author,
            post_type=ForumPost.PostType.OPENING,
            content=initial_post_content,
        )
        # Initialize comment_count
        thread.comment_count = 1
        thread.save(update_fields=['comment_count'])
        return thread


class ForumVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumVote
        fields = ['id', 'post', 'vote_type']

    def create(self, validated_data):
        user = validated_data.pop('user', None) or self.context['request'].user
        post = validated_data['post']
        vote_type = validated_data['vote_type']

        vote, created = ForumVote.objects.update_or_create(
            user=user, post=post,
            defaults={'vote_type': vote_type},
        )
        # Refresh cached score on the post
        post.refresh_score()
        return vote


class ForumBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumBookmark
        fields = ['id', 'thread', 'created_at']
        read_only_fields = ['created_at']


class ForumReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.username', read_only=True)
    post_thread_slug = serializers.CharField(source='post.thread.slug', read_only=True)

    class Meta:
        model = ForumReport
        fields = ['id', 'reporter', 'reporter_name', 'post', 'post_thread_slug',
                  'reason', 'details', 'resolved', 'created_at']
        read_only_fields = ['reporter', 'resolved', 'created_at']
