import hashlib
import re
import threading
import time

from .models import PageView, ActiveSession


class AnalyticsMiddleware:
    """Middleware to track page views and active sessions.

    PageView records are buffered in memory and flushed via bulk_create
    every BUFFER_SIZE inserts or FLUSH_INTERVAL seconds — whichever comes
    first.  This turns N individual INSERTs into a single multi-row INSERT,
    dramatically reducing DB round-trips under load.
    """

    BUFFER_SIZE = 50          # max records before forced flush
    FLUSH_INTERVAL = 10       # seconds between time-based flushes
    ACTIVE_SESSION_PING_TTL = 15  # seconds

    BOT_SIGNATURES = (
        'bot', 'spider', 'crawler', 'crawl', 'slurp', 'fetcher',
        'facebookexternalhit', 'whatsapp', 'telegrambot', 'discordbot',
        'bingpreview', 'headless', 'python-requests', 'httpclient',
        'uptime', 'healthcheck', 'monitor',
    )

    _buffer: list = []
    _buffer_lock = threading.Lock()
    _last_flush: float = 0.0  # monotonic timestamp of last flush
    _active_ping: dict = {}
    _active_ping_lock = threading.Lock()
    
    # Paths to exclude from tracking
    EXCLUDED_PATTERNS = [
        r'^/static/',
        r'^/media/',
        r'^/jsi18n/',
        r'^/favicon',
        r'^/__debug__/',
        r'^/admin/jsi18n/',
        r'^/analytics/',
        r'^/database/',
        r'^/health',
        r'\.ico$',
        r'\.js$',
        r'\.css$',
        r'\.png$',
        r'\.jpg$',
        r'\.gif$',
        r'\.svg$',
        r'\.woff',
        r'\.ttf$',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_re = [re.compile(p) for p in self.EXCLUDED_PATTERNS]
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Track successful page loads AND 404s (for broken link diagnosis)
        if response.status_code in (200, 404):
            self.track_request(request)
        
        return response
    
    def should_track(self, path):
        """Check if this path should be tracked."""
        for pattern in self.excluded_re:
            if pattern.search(path):
                return False
        return True
    
    def get_client_ip(self, request):
        """Get the client's real IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def parse_user_agent(self, ua_string):
        """Simple user agent parsing."""
        ua = ua_string.lower()
        
        # Device type
        if ('mobile' in ua or 'android' in ua) and 'tablet' not in ua:
            device = 'Mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device = 'Tablet'
        else:
            device = 'Desktop'
        
        # Browser
        if 'firefox' in ua:
            browser = 'Firefox'
        elif 'edg' in ua:
            browser = 'Edge'
        elif 'chrome' in ua:
            browser = 'Chrome'
        elif 'safari' in ua:
            browser = 'Safari'
        elif 'opera' in ua or 'opr' in ua:
            browser = 'Opera'
        else:
            browser = 'Other'
        
        # OS
        if 'windows' in ua:
            os = 'Windows'
        elif 'mac os' in ua or 'macos' in ua:
            os = 'macOS'
        elif 'linux' in ua:
            os = 'Linux'
        elif 'android' in ua:
            os = 'Android'
        elif 'iphone' in ua or 'ipad' in ua:
            os = 'iOS'
        else:
            os = 'Other'
        
        return device, browser, os

    def is_probable_bot(self, ua_string):
        """Best-effort bot detection for human-centric analytics."""
        ua = (ua_string or '').lower()
        if not ua:
            return False
        return any(sig in ua for sig in self.BOT_SIGNATURES)

    def get_visitor_key(self, request, ip_address, user_agent, user):
        """Return a stable visitor key without forcing Django session creation."""
        if user and getattr(user, 'is_authenticated', False):
            return f'user:{user.pk}'

        existing_session = getattr(request.session, 'session_key', None)
        if existing_session:
            return f'sess:{existing_session}'

        # Anonymous fallback for clients that block cookies.
        source = f"{ip_address or '-'}|{(user_agent or '')[:160]}"
        digest = hashlib.sha256(source.encode('utf-8', errors='ignore')).hexdigest()[:32]
        return f'anon:{digest}'

    @classmethod
    def _should_touch_active_session(cls, session_key):
        """In-process throttle for ActiveSession writes."""
        now = time.monotonic()
        with cls._active_ping_lock:
            last = cls._active_ping.get(session_key)
            if last is not None and (now - last) < cls.ACTIVE_SESSION_PING_TTL:
                return False
            cls._active_ping[session_key] = now

            # Opportunistic cleanup to prevent unbounded memory growth.
            if len(cls._active_ping) > 5000:
                cutoff = now - (cls.ACTIVE_SESSION_PING_TTL * 2)
                cls._active_ping = {
                    key: ts for key, ts in cls._active_ping.items()
                    if ts >= cutoff
                }
            return True
    
    def track_request(self, request):
        """Track the page view and update active session."""
        path = request.path

        # When served via a tournament subdomain, the middleware rewrites
        # request.path to include a /<slug>/ prefix.  Strip it so that
        # analytics records the *real* URL the user sees.
        subdomain_slug = getattr(request, 'subdomain_tournament', None)
        if subdomain_slug:
            slug_prefix = f'/{subdomain_slug}/'
            display_path = '/' + path[len(slug_prefix):] if path.startswith(slug_prefix) else path
        else:
            display_path = path
        
        if not self.should_track(path):
            return
        
        try:
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            referer = request.META.get('HTTP_REFERER', '')
            user = request.user if request.user.is_authenticated else None

            # Keep dashboard traffic metrics human-centric.
            if self.is_probable_bot(user_agent):
                return

            session_key = self.get_visitor_key(request, ip_address, user_agent, user)
            
            device, browser, os = self.parse_user_agent(user_agent)

            # Build the canonical full URL (subdomain-aware)
            if subdomain_slug:
                from django.conf import settings
                base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
                scheme = 'https' if request.is_secure() else 'http'
                full_url = f'{scheme}://{subdomain_slug}.{base_domain}{display_path}'
            else:
                full_url = request.build_absolute_uri()
            
            # Buffer the page view for bulk insertion
            pv = PageView(
                path=display_path,
                full_url=full_url,
                session_key=session_key,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else '',
                referer=referer[:1000] if referer else '',
                device_type=device,
                browser=browser,
                os=os,
            )
            self._enqueue(pv)

            # Avoid DB write amplification by only touching active sessions every N seconds.
            if self._should_touch_active_session(session_key):
                ActiveSession.objects.update_or_create(
                    session_key=session_key,
                    defaults={
                        'user': user,
                        'ip_address': ip_address,
                        'current_path': display_path,
                    }
                )
            
            # Periodically clean up stale sessions (1% of requests)
            import random
            if random.random() < 0.01:
                ActiveSession.cleanup_stale()
                
        except Exception:
            # Don't break the site for analytics — but log so we can debug
            import logging
            logging.getLogger(__name__).warning('Analytics tracking failed', exc_info=True)

    # ------------------------------------------------------------------
    # Write-behind buffer helpers
    # ------------------------------------------------------------------

    @classmethod
    def _enqueue(cls, page_view):
        """Add a PageView to the buffer and flush if thresholds are met."""
        with cls._buffer_lock:
            cls._buffer.append(page_view)
            now = time.monotonic()
            should_flush = (
                len(cls._buffer) >= cls.BUFFER_SIZE
                or (now - cls._last_flush) >= cls.FLUSH_INTERVAL
            )
        if should_flush:
            cls._flush()

    @classmethod
    def _flush(cls):
        """Bulk-write buffered PageView records to the database."""
        with cls._buffer_lock:
            if not cls._buffer:
                return
            batch = cls._buffer[:]
            cls._buffer = []
            cls._last_flush = time.monotonic()
        try:
            PageView.objects.bulk_create(batch, ignore_conflicts=True)
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'Analytics bulk flush failed for %d records', len(batch),
                exc_info=True,
            )
