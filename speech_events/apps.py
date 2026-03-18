from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpeechEventsConfig(AppConfig):
    name = 'speech_events'
    verbose_name = _("Speech Events")
