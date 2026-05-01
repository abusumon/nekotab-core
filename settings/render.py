import logging
import os

import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .core import TABBYCAT_VERSION

logger = logging.getLogger(__name__)

# ==============================================================================
# Render per https://render.com/docs/deploy-django
# ==============================================================================

# Store Tab Director Emails for reporting purposes
if os.environ.get('TAB_DIRECTOR_EMAIL', ''):
    TAB_DIRECTOR_EMAIL = os.environ.get('TAB_DIRECTOR_EMAIL')

if os.environ.get('DJANGO_SECRET_KEY', ''):
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# https://docs.djangoproject.com/en/3.0/ref/settings/#allowed-hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '.nekotab.app').split(',')

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ==============================================================================
# Subdomain routing (production defaults)
# ==============================================================================

SUBDOMAIN_BASE_DOMAIN = os.environ.get('SUBDOMAIN_BASE_DOMAIN', '').strip()
_subdomain_tournaments_requested = os.environ.get('SUBDOMAIN_TOURNAMENTS_ENABLED', 'true').lower() == 'true'
SUBDOMAIN_TOURNAMENTS_ENABLED = _subdomain_tournaments_requested and bool(SUBDOMAIN_BASE_DOMAIN)
if _subdomain_tournaments_requested and not SUBDOMAIN_BASE_DOMAIN:
    logger.warning(
        'SUBDOMAIN_TOURNAMENTS_ENABLED is true but SUBDOMAIN_BASE_DOMAIN is empty; '
        'subdomain routing is disabled.'
    )
RESERVED_SUBDOMAINS = os.environ.get('RESERVED_SUBDOMAINS', 'www,admin,api,jet,database,static,media').split(',')

# Organization workspace routing; when False, SubdomainTenantMiddleware
# behaves identically to the old SubdomainTournamentMiddleware.
ORGANIZATION_WORKSPACES_ENABLED = os.environ.get('ORGANIZATION_WORKSPACES_ENABLED', 'false').lower() == 'true'

# Share cookies across subdomains when base domain is configured.
# This is safe because tournament owners do NOT have the ability to run
# arbitrary server code or set cookies on their subdomains — all subdomains
# are served by the same Render app.  Without this, users lose their
# authenticated session when redirected from the base domain to a tournament
# subdomain (e.g., after creating a tournament).
if SUBDOMAIN_BASE_DOMAIN:
    SESSION_COOKIE_DOMAIN = f".{SUBDOMAIN_BASE_DOMAIN}"
    SESSION_COOKIE_NAME = 'nekotab_sessionid'
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_DOMAIN = f".{SUBDOMAIN_BASE_DOMAIN}"
    CSRF_COOKIE_SAMESITE = 'Lax'
    csrf_trusted = [
        f"https://{SUBDOMAIN_BASE_DOMAIN}",
        f"https://*.{SUBDOMAIN_BASE_DOMAIN}",
    ]
    try:
        CSRF_TRUSTED_ORIGINS = list(set(globals().get('CSRF_TRUSTED_ORIGINS', []) + csrf_trusted))
    except Exception:
        CSRF_TRUSTED_ORIGINS = csrf_trusted

# ==============================================================================
# Postgres
# ==============================================================================

# Parse database configuration from $DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        # Feel free to alter this value to suit your needs.
        default='postgresql://postgres:postgres@localhost:5432/mysite',
        conn_max_age=600
    )
}

# ==============================================================================
# Redis
# ==============================================================================

_redis_url = os.environ.get('REDIS_URL', '').strip()
if not _redis_url:
    _redis_host = os.environ.get('REDIS_HOST', '').strip()
    _redis_port = os.environ.get('REDIS_PORT', '').strip()
    if _redis_host and _redis_port:
        _redis_url = f"redis://{_redis_host}:{_redis_port}"

if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 60,
                "IGNORE_EXCEPTIONS": True,  # Don't crash on cache connection issues.
            },
        },
    }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [_redis_url],
            },
        },
    }

# ==============================================================================
# Sentry
# ==============================================================================

if not os.environ.get('DISABLE_SENTRY'):
    DISABLE_SENTRY = False
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN', ''),
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(event_level=logging.WARNING),
            RedisIntegration(),
        ],
        send_default_pii=False,
        release=TABBYCAT_VERSION,
    )
