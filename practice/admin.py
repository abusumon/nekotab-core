from django.contrib import admin
from .models import PracticeSession, SessionRoom, SessionParticipant, SpeakerScore


class SessionRoomInline(admin.TabularInline):
    model = SessionRoom
    extra = 0


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'date', 'format', 'status', 'created_by']
    list_filter = ['organization', 'status', 'format']
    search_fields = ['title', 'organization__name']
    inlines = [SessionRoomInline, SessionParticipantInline]


@admin.register(SpeakerScore)
class SpeakerScoreAdmin(admin.ModelAdmin):
    list_display = ['participant', 'score', 'reply_score', 'won', 'submitted_at']
    list_filter = ['won']
