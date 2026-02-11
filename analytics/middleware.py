import re
from django.utils import timezone
from .models import PageView, ActiveSession


class AnalyticsMiddleware:
    """Middleware to track page views and active sessions."""
    
    # Paths to exclude from tracking
    EXCLUDED_PATTERNS = [
        r'^/static/',
        r'^/media/',
        r'^/jsi18n/',
        r'^/favicon',
        r'^/__debug__/',
        r'^/admin/jsi18n/',
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
        
        # Only track successful page loads
        if response.status_code == 200:
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
        if 'mobile' in ua or 'android' in ua and 'mobile' in ua:
            device = 'mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device = 'tablet'
        else:
            device = 'desktop'
        
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
    
    def track_request(self, request):
        """Track the page view and update active session."""
        path = request.path
        
        if not self.should_track(path):
            return
        
        try:
            # Get or create session key
            if not request.session.session_key:
                request.session.save()
            session_key = request.session.session_key or 'anonymous'
            
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            referer = request.META.get('HTTP_REFERER', '')
            
            device, browser, os = self.parse_user_agent(user_agent)
            
            user = request.user if request.user.is_authenticated else None
            
            # Create page view record
            PageView.objects.create(
                path=path,
                full_url=request.build_absolute_uri(),
                session_key=session_key,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else '',
                referer=referer[:1000] if referer else '',
                device_type=device,
                browser=browser,
                os=os,
            )
            
            # Update active session
            ActiveSession.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'user': user,
                    'ip_address': ip_address,
                    'current_path': path,
                    'last_activity': timezone.now(),
                }
            )
            
            # Periodically clean up stale sessions (1% of requests)
            import random
            if random.random() < 0.01:
                ActiveSession.cleanup_stale()
                
        except Exception:
            # Silently fail - don't break the site for analytics
            pass
