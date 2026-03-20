"""JWT utilities for congress events — issue tokens for nekocongress API."""

from datetime import datetime, timedelta, timezone

from django.conf import settings as django_settings
from jose import jwt


def issue_congress_token(user, role='director', tournament_id=None) -> str:
    """Issue a JWT for nekocongress API access.

    Tokens are signed with the shared Django SECRET_KEY so nekocongress
    can verify them without a separate auth service.
    """
    secret = getattr(django_settings, 'NEKOCONGRESS_JWT_SECRET',
                     django_settings.SECRET_KEY)
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id if hasattr(user, 'id') else 0,
        'username': str(user),
        'role': role,
        'tournament_id': tournament_id,
        'iat': now,
        'exp': now + timedelta(hours=12),
    }
    return jwt.encode(payload, secret, algorithm='HS256')
