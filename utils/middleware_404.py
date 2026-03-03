"""
Middleware to log 404 responses for diagnostic purposes.

Logs: path, referer, user-agent, timestamp, IP address.
Helps identify broken internal links, old indexed URLs, and external backlinks
hitting dead pages.

Register in settings.py MIDDLEWARE (after CommonMiddleware):
    'utils.middleware_404.Log404Middleware',
"""

import logging
from django.utils import timezone

logger = logging.getLogger('nekotab.404')


class Log404Middleware:
    """Log every 404 response with diagnostic context.

    Output goes to the 'nekotab.404' logger so it can be routed to
    a file, Sentry, or Heroku's log drain independently of other loggers.
    """

    # Known bot user-agent substrings (case-insensitive)
    BOT_SIGNATURES = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'sogou', 'exabot', 'facebot', 'ia_archiver',
        'semrushbot', 'ahrefsbot', 'mj12bot', 'dotbot', 'petalbot',
        'bytespider', 'gptbot', 'claudebot', 'applebot',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code == 404:
            self._log_404(request)

        return response

    def _log_404(self, request):
        path = request.get_full_path()
        referer = request.META.get('HTTP_REFERER', '-')
        user_agent = request.META.get('HTTP_USER_AGENT', '-')
        ip = self._get_client_ip(request)
        now = timezone.now().isoformat()
        source = self._classify_source(request, referer, user_agent)

        logger.warning(
            '404 | path=%s | referer=%s | ua=%s | ip=%s | source=%s | time=%s',
            path,
            referer[:200],
            user_agent[:200],
            ip,
            source,
            now,
        )

    def _get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '?')

    def _classify_source(self, request, referer, user_agent):
        """Classify the 404 source as bot, internal, external, or direct."""
        ua_lower = user_agent.lower()
        for sig in self.BOT_SIGNATURES:
            if sig in ua_lower:
                return 'bot:' + sig

        if referer and referer != '-':
            host = request.get_host()
            if host and host in referer:
                return 'internal'
            return 'external'

        return 'direct'
