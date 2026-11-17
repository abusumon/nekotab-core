"""Error handlers that can't themselves turn into a 500.

Django renders 400/403/404 pages inside ``get_exception_response``, and if that
rendering raises, Django swallows the exception and serves the 500 page with no
traceback in the logs. In production that happened ~300 times a day: favicon
requests on tournament subdomains, unreleased results pages and scanner probes
all showed "Internal Server Error" instead of "Page Not Found".

The rendering failures came from long-running ASGI workers that reversed URLs
against the organisation workspace URLconf, so ``{% url 'motions' %}`` in the
main 404 template raised NoReverseMatch. These wrappers log the real exception
together with the URLconf that was active, retry once against ROOT_URLCONF, and
fall back to a plain page with the correct status code if that fails too.
"""

import logging

from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         HttpResponseNotFound)
from django.urls import get_urlconf, set_urlconf
from django.views import defaults

logger = logging.getLogger(__name__)

_FALLBACK = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<meta name="robots" content="noindex, nofollow">'
    '<title>{title} - NekoTab</title></head>'
    '<body style="font-family:system-ui,sans-serif;max-width:36rem;margin:4rem auto;padding:0 1rem">'
    '<h1>{title}</h1><p>{message}</p><p><a href="/">Go to the homepage</a></p></body></html>'
)


def _render_safely(default_view, fallback_class, title, message, request, exception):
    try:
        return default_view(request, exception)
    except Exception:
        logger.exception(
            'Error page for %s failed to render (urlconf=%r); retrying with ROOT_URLCONF',
            request.path, get_urlconf(),
        )

    set_urlconf(None)
    try:
        return default_view(request, exception)
    except Exception:
        logger.exception('Error page for %s failed again; serving the plain fallback', request.path)

    return fallback_class(_FALLBACK.format(title=title, message=message))


def page_not_found(request, exception):
    return _render_safely(
        defaults.page_not_found, HttpResponseNotFound,
        'Page Not Found (404)', "Sorry, there doesn't appear to be a page at this URL.",
        request, exception)


def permission_denied(request, exception):
    return _render_safely(
        defaults.permission_denied, HttpResponseForbidden,
        'Forbidden (403)', "This page isn't available right now.",
        request, exception)


def bad_request(request, exception):
    return _render_safely(
        defaults.bad_request, HttpResponseBadRequest,
        'Bad Request (400)', 'The request could not be understood.',
        request, exception)
