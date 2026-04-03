import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from participants.models import Adjudicator, Speaker

logger = logging.getLogger(__name__)


def _sync_to_crm(email, name, is_debater=False, is_adjudicator=False, tournament=None):
    """Upsert a ParticipantProfile with smart hybrid detection.

    If a speaker is saved and the existing profile is already 'adjudicator',
    the role is promoted to 'hybrid' rather than overwritten.
    """
    from participant_crm.models import ParticipantProfile

    email = email.strip().lower()
    if not email:
        return

    try:
        profile = ParticipantProfile.objects.get(email=email)
        profile.name = name
        profile.last_active = timezone.now()

        # Promote to hybrid when both roles are detected
        if is_debater and profile.primary_role == ParticipantProfile.ROLE_ADJUDICATOR:
            profile.primary_role = ParticipantProfile.ROLE_HYBRID
        elif is_adjudicator and profile.primary_role == ParticipantProfile.ROLE_DEBATER:
            profile.primary_role = ParticipantProfile.ROLE_HYBRID
        elif is_debater and profile.primary_role not in (
            ParticipantProfile.ROLE_DEBATER, ParticipantProfile.ROLE_HYBRID,
        ):
            profile.primary_role = ParticipantProfile.ROLE_DEBATER
        elif is_adjudicator and profile.primary_role not in (
            ParticipantProfile.ROLE_ADJUDICATOR, ParticipantProfile.ROLE_HYBRID,
        ):
            profile.primary_role = ParticipantProfile.ROLE_ADJUDICATOR

        profile.save(update_fields=['name', 'last_active', 'primary_role'])

        if tournament:
            profile.tournaments_participated.add(tournament)

    except ParticipantProfile.DoesNotExist:
        role = ParticipantProfile.ROLE_DEBATER if is_debater else ParticipantProfile.ROLE_ADJUDICATOR
        profile = ParticipantProfile.objects.create(
            email=email,
            name=name,
            primary_role=role,
            last_active=timezone.now(),
            source_tournament=tournament,
        )
        if tournament:
            profile.tournaments_participated.add(tournament)


@receiver(post_save, sender=Speaker)
def sync_speaker_to_crm(sender, instance, **kwargs):
    if instance.email:
        tournament = getattr(instance.team, 'tournament', None) if instance.team else None
        _sync_to_crm(email=instance.email, name=instance.name,
                      is_debater=True, tournament=tournament)


@receiver(post_save, sender=Adjudicator)
def sync_adjudicator_to_crm(sender, instance, **kwargs):
    if instance.email:
        _sync_to_crm(email=instance.email, name=instance.name,
                      is_adjudicator=True, tournament=instance.tournament)
