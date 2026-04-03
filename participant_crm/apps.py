from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ParticipantCrmConfig(AppConfig):
    name = 'participant_crm'
    verbose_name = _("Participant CRM")

    def ready(self):
        from . import signals  # noqa: F401
