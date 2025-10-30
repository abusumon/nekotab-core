import string

from tournaments.models import Tournament
from utils.misc import generate_identifier_string

from .models import Invitation


def populate_invitation_url_keys(instances: list[Invitation], tournament: Tournament, length: int = 15, num_attempts: int = 10) -> None:
    """Populates the URL key field for every instance in the given QuerySet."""
    chars = string.ascii_lowercase + string.digits

    existing_keys = list(Invitation.objects.exclude(url_key__isnull=True).values_list('url_key', flat=True))
    for instance in instances:
        for i in range(num_attempts):
            new_key = generate_identifier_string(chars, length)
            if new_key not in existing_keys:
                instance.url_key = new_key
                existing_keys.append(new_key)
                break
