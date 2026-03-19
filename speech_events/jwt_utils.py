"""JWT token issuance for individual events.

Generates short-lived JWTs signed with Django's SECRET_KEY so the
browser-based Vue components can authenticate with the nekospeech API.
The token carries the user's id and role ('director' or 'judge').
"""

import time

from django.conf import settings
from jose import jwt


def issue_ie_token(user, *, role="director", ttl_seconds=3600):
    """Return a signed JWT for the given Django user.

    Args:
        user: Django User instance (must be authenticated).
        role: 'director' or 'judge'.
        ttl_seconds: Token lifetime in seconds (default 1 hour).

    Returns:
        Encoded JWT string.
    """
    import hashlib, sys
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:16]
    print(f"JWT_SIGN_DEBUG: key_len={len(settings.SECRET_KEY)} key_sha256_prefix={key_hash} key_first5={repr(settings.SECRET_KEY[:5])}", file=sys.stderr, flush=True)
    now = int(time.time())
    payload = {
        "user_id": user.id,
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def issue_judge_ballot_token(*, judge_id, room_id, event_id, tournament_id, ttl_seconds=7200):
    """Return a signed JWT scoped to a judge's single room assignment.

    This token is used for tokenized ballot URLs — judges don't need to log in.
    The token is scoped to a specific room so a judge cannot access other rooms.

    Args:
        judge_id: Adjudicator person_ptr_id.
        room_id: ie_room.id the judge is assigned to.
        event_id: speech_event.id.
        tournament_id: Tournament ID.
        ttl_seconds: Token lifetime (default 2 hours, longer for judge convenience).

    Returns:
        Encoded JWT string.
    """
    now = int(time.time())
    payload = {
        "judge_id": judge_id,
        "room_id": room_id,
        "event_id": event_id,
        "tournament_id": tournament_id,
        "role": "judge",
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
