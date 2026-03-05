from django.contrib import admin

from utils.admin import ModelAdmin
from utils.admin_tenant import TournamentScopedAdminMixin

from .models import Answer, Invitation, Question


@admin.register(Answer)
class AnswerAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'question__tournament'
    list_display = ('question', 'answer', 'content_object')
    list_filter = ('question',)


@admin.register(Question)
class QuestionAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('name', 'tournament', 'for_content_type', 'answer_type')
    list_filter = ('tournament', 'for_content_type')


@admin.register(Invitation)
class InvitationAdmin(TournamentScopedAdminMixin, ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('url_key', 'institution', 'team')
