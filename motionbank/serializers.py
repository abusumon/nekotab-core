from rest_framework import serializers
from .models import (
    MotionEntry, MotionAnalysis, MotionStats,
    MotionRating, CaseOutline, CaseOutlineVote, PracticeSession,
)


class MotionStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotionStats
        fields = [
            'times_practiced', 'times_used_in_tournaments',
            'forum_thread_count', 'average_rating', 'total_ratings',
            'gov_win_rate',
        ]


class MotionAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotionAnalysis
        fields = [
            'ai_analysis', 'model_used', 'confidence_score', 'last_updated',
        ]


class CaseOutlineSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    side_display = serializers.CharField(source='get_side_display', read_only=True)
    user_voted = serializers.SerializerMethodField()

    class Meta:
        model = CaseOutline
        fields = [
            'id', 'motion', 'author', 'author_name', 'side', 'side_display',
            'title', 'content', 'upvotes', 'user_voted',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['author', 'upvotes', 'created_at', 'updated_at']

    def get_user_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.votes.filter(user=request.user).exists()
        return False


class MotionEntryListSerializer(serializers.ModelSerializer):
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    type_display = serializers.CharField(source='get_motion_type_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    prep_display = serializers.CharField(source='get_prep_type_display', read_only=True)
    stats = MotionStatsSerializer(read_only=True)
    has_analysis = serializers.SerializerMethodField()

    class Meta:
        model = MotionEntry
        fields = [
            'id', 'text', 'slug', 'info_slide',
            'format', 'format_display',
            'motion_type', 'type_display',
            'difficulty', 'difficulty_display',
            'prep_type', 'prep_display',
            'tournament_name', 'year', 'region', 'round_info',
            'theme_tags', 'source',
            'stats', 'has_analysis',
            'created_at',
        ]

    def get_has_analysis(self, obj):
        return hasattr(obj, 'analysis')


class MotionEntryDetailSerializer(MotionEntryListSerializer):
    analysis = MotionAnalysisSerializer(read_only=True)
    case_outlines = CaseOutlineSerializer(many=True, read_only=True)
    forum_threads = serializers.SerializerMethodField()
    related_motions = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

    class Meta(MotionEntryListSerializer.Meta):
        fields = MotionEntryListSerializer.Meta.fields + [
            'analysis', 'case_outlines', 'forum_threads',
            'related_motions', 'user_rating',
        ]

    def get_forum_threads(self, obj):
        from forum.serializers import ForumThreadListSerializer
        threads = obj.forum_threads.all()[:5]
        return ForumThreadListSerializer(threads, many=True, context=self.context).data

    def get_related_motions(self, obj):
        """Find related motions by shared theme tags or similar text."""
        if not obj.theme_tags:
            return []
        from django.db.models import Q
        related = MotionEntry.objects.filter(
            is_approved=True,
        ).exclude(pk=obj.pk)

        # Filter by overlapping theme tags
        q = Q()
        for tag in obj.theme_tags[:3]:
            q |= Q(theme_tags__contains=[tag])
        related = related.filter(q)[:5]

        return MotionEntryListSerializer(related, many=True, context=self.context).data

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rating = obj.ratings.filter(user=request.user).first()
            return rating.score if rating else None
        return None


class MotionEntryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotionEntry
        fields = [
            'text', 'info_slide', 'format', 'motion_type', 'difficulty',
            'prep_type', 'tournament_name', 'year', 'region', 'round_info',
            'theme_tags', 'source',
        ]

    def create(self, validated_data):
        from django.utils.text import slugify
        import uuid
        base_slug = slugify(validated_data['text'])[:300]
        validated_data['slug'] = f"{base_slug}-{uuid.uuid4().hex[:8]}"
        validated_data['submitted_by'] = self.context['request'].user

        motion = MotionEntry.objects.create(**validated_data)
        MotionStats.objects.create(motion=motion)
        return motion


class MotionRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotionRating
        fields = ['id', 'motion', 'score']

    def validate_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Score must be between 1 and 5")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        rating, created = MotionRating.objects.update_or_create(
            user=user, motion=validated_data['motion'],
            defaults={'score': validated_data['score']},
        )

        # Update stats
        motion = validated_data['motion']
        from django.db.models import Avg
        stats, _ = MotionStats.objects.get_or_create(motion=motion)
        agg = motion.ratings.aggregate(avg=Avg('score'))
        stats.average_rating = agg['avg'] or 0
        stats.total_ratings = motion.ratings.count()
        stats.save()

        return rating


class MotionDoctorInputSerializer(serializers.Serializer):
    """Input for the Motion Doctor analysis tool."""
    motion_text = serializers.CharField(max_length=1000)
    format = serializers.ChoiceField(choices=MotionEntry.MotionFormat.choices, required=False)
    info_slide = serializers.CharField(required=False, allow_blank=True)


class PracticeSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeSession
        fields = ['id', 'motion', 'side_practiced', 'notes', 'duration_minutes', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        session = super().create(validated_data)

        # Update stats
        stats, _ = MotionStats.objects.get_or_create(motion=validated_data['motion'])
        stats.times_practiced += 1
        stats.save()

        return session
