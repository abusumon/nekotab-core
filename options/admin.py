from django.contrib import admin
from django_summernote.utils import get_attachment_model
from dynamic_preferences.admin import PerInstancePreferenceAdmin

from utils.admin_tenant import TournamentScopedAdminMixin

from .models import TournamentPreferenceModel


# ==============================================================================
# Preferences
# ==============================================================================

@admin.register(TournamentPreferenceModel)
class TournamentPreferenceAdmin(TournamentScopedAdminMixin, PerInstancePreferenceAdmin):
    tournament_lookup = 'instance'


# We don't use the attachment model; so hide it in the admin area
admin.site.unregister(get_attachment_model())
