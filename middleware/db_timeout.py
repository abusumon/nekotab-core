"""Middleware that converts Postgres statement_timeout errors into clean 503 responses.

When a query exceeds the 30-second statement_timeout set in digitalocean.py,
Postgres raises an OperationalError with 'statement timeout' in the message.
Without this middleware the error surfaces as a 500 and Django's debug page
(or Sentry) would capture it as an unexpected crash. This handler:
  - Logs the timed-out path and authenticated user at ERROR level.
  - Returns a JSON 503 for /api/ paths so API clients can retry.
  - Returns a minimal HTML 503 page for browser paths.
  - Re-raises every other OperationalError so genuine DB failures still crash
    loudly and get caught by Sentry / the error handler.
"""

import logging

from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

_TIMEOUT_MARKER = 'statement timeout'

_HTML_503 = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<title>503 – Request timed out</title></head><body>'
    '<h1>503 Service Unavailable</h1>'
    '<p>The request took too long to complete. Please try again in a moment.</p>'
    '</body></html>'
)


class QueryTimeoutMiddleware:
    """Catch Postgres statement_timeout OperationalErrors and return 503."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except OperationalError as exc:
            if _TIMEOUT_MARKER in str(exc).lower():
                user = getattr(request, 'user', None)
                username = getattr(user, 'username', 'anonymous') if user else 'anonymous'
                logger.error(
                    'DB statement timeout: path=%s user=%s',
                    request.path,
                    username,
                )
                if request.path.startswith('/api/'):
                    return JsonResponse(
                        {'error': 'Request timed out. Please try again.'},
                        status=503,
                    )
                return HttpResponse(_HTML_503, status=503, content_type='text/html; charset=utf-8')
            # Not a timeout — let it propagate to Sentry / Django's 500 handler.
            raise
