from rest_framework import serializers
from .models import (
    DebatePassport, TournamentParticipation, RoundPerformance,
    JudgeBallot, Partnership, UserStats,
)


class RoundPerformanceSerializer(serializers.ModelSerializer):
    side_display = serializers.CharField(source='get_side_display', read_only=True)
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)

    class Meta:
        model = RoundPerformance
        fields = [
            'id', 'round_number', 'round_name',
            'side', 'side_display', 'position', 'position_display',
            'result', 'result_display', 'speaker_score',
            'average_score_in_round', 'motion_text',
        ]
        read_only_fields = ['id']


class JudgeBallotSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudgeBallot
        fields = [
            'id', 'round_number', 'round_name',
            'was_chair', 'panel_size', 'agreed_with_majority',
            'scores_given', 'motion_text',
        ]
        read_only_fields = ['id']


class TournamentParticipationSerializer(serializers.ModelSerializer):
    round_performances = RoundPerformanceSerializer(many=True, read_only=True)
    judge_ballots = JudgeBallotSerializer(many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    format_display = serializers.CharField(source='get_tournament_format_display', read_only=True)

    class Meta:
        model = TournamentParticipation
        fields = [
            'id', 'tournament_name', 'tournament_format', 'format_display',
            'year', 'location', 'num_rounds',
            'role', 'role_display', 'team_name', 'partner_names',
            'broke', 'break_category', 'final_rank', 'verified',
            'round_performances', 'judge_ballots',
            'created_at',
        ]
        read_only_fields = ['verified', 'created_at']


class TournamentParticipationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TournamentParticipation
        fields = [
            'tournament_name', 'tournament_format', 'year', 'location',
            'num_rounds', 'role', 'team_name', 'partner_names',
            'broke', 'break_category', 'final_rank',
        ]


class PartnershipSerializer(serializers.ModelSerializer):
    win_rate = serializers.FloatField(read_only=True)
    avg_speaker_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Partnership
        fields = [
            'id', 'partner_name', 'partner_passport',
            'tournaments_together', 'rounds_together',
            'wins_together', 'win_rate', 'avg_speaker_score',
        ]


class SkillRadarSerializer(serializers.Serializer):
    framing = serializers.FloatField()
    clash = serializers.FloatField()
    extension = serializers.FloatField()
    weighing = serializers.FloatField()
    rebuttal = serializers.FloatField()
    strategy = serializers.FloatField()
    delivery = serializers.FloatField()


class UserStatsSerializer(serializers.ModelSerializer):
    skill_radar = serializers.SerializerMethodField()

    class Meta:
        model = UserStats
        fields = [
            'total_tournaments', 'total_rounds', 'break_rate',
            'average_speaker_score', 'highest_speaker_score',
            'overall_win_rate', 'gov_win_rate', 'opp_win_rate',
            'format_distribution', 'skill_radar',
            'judge_total_rounds', 'judge_chair_rate',
            'judge_avg_score_given', 'judge_score_variance',
            'judge_majority_agreement',
            'performance_trend', 'last_computed',
        ]

    def get_skill_radar(self, obj):
        return {
            'framing': obj.skill_framing,
            'clash': obj.skill_clash,
            'extension': obj.skill_extension,
            'weighing': obj.skill_weighing,
            'rebuttal': obj.skill_rebuttal,
            'strategy': obj.skill_strategy,
            'delivery': obj.skill_delivery,
        }


class DebatePassportListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    format_display = serializers.CharField(source='get_primary_format_display', read_only=True)
    level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    badges = serializers.SerializerMethodField()

    class Meta:
        model = DebatePassport
        fields = [
            'id', 'user', 'username', 'display_name', 'bio',
            'country', 'country_code', 'institution',
            'primary_format', 'format_display',
            'experience_level', 'level_display',
            'is_speaker', 'is_judge', 'is_ca', 'is_coach',
            'avatar_url', 'badges',
        ]

    def get_badges(self, obj):
        from forum.serializers import UserBadgeSerializer
        return UserBadgeSerializer(obj.user.forum_badges.filter(verified=True), many=True).data


class DebatePassportDetailSerializer(DebatePassportListSerializer):
    participations = TournamentParticipationSerializer(many=True, read_only=True)
    partnerships = PartnershipSerializer(many=True, read_only=True)
    stats = UserStatsSerializer(source='cached_stats', read_only=True)

    class Meta(DebatePassportListSerializer.Meta):
        fields = DebatePassportListSerializer.Meta.fields + [
            'participations', 'partnerships', 'stats',
            'show_scores', 'show_analytics', 'is_public',
            'timezone', 'created_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        # Respect privacy settings
        is_owner = request and request.user == instance.user
        if not is_owner:
            if not instance.show_scores:
                # Remove score data from rounds
                for p in data.get('participations', []):
                    for r in p.get('round_performances', []):
                        r.pop('speaker_score', None)
            if not instance.show_analytics:
                data.pop('stats', None)

        return data


class DebatePassportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebatePassport
        fields = [
            'display_name', 'bio', 'country', 'country_code', 'institution',
            'primary_format', 'experience_level',
            'is_speaker', 'is_judge', 'is_ca', 'is_coach',
            'is_public', 'show_scores', 'show_analytics',
            'avatar_url', 'timezone',
        ]
