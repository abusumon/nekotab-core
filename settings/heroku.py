import logging
from os import environ

import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .core import NekoTab_VERSION

# ==============================================================================
# Heroku
# ==============================================================================

# Store Tab Director Emails for reporting purposes
if environ.get('TAB_DIRECTOR_EMAIL', ''):
    TAB_DIRECTOR_EMAIL = environ.get('TAB_DIRECTOR_EMAIL')

if environ.get('DJANGO_SECRET_KEY', ''):
    SECRET_KEY = environ.get('DJANGO_SECRET_KEY')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Require HTTPS
if 'DJANGO_SECRET_KEY' in environ and environ.get('DISABLE_HTTPS_REDIRECTS', '') != 'disable':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ==============================================================================
# Postgres
# ==============================================================================

# Parse database configuration from $DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(default='postgres://localhost'),
}

# ==============================================================================
# Redis
# ==============================================================================

# Use a separate Redis addon for channels to reduce number of connections
# With fallback for Tabbykitten installs (no addons) or pre-2.2 instances
# Prefer a TLS URL when provided by the add-on (e.g., REDIS_TLS_URL)
REDIS_TLS_URL = environ.get('REDIS_TLS_URL')
REDISCLOUD_URL = environ.get('REDISCLOUD_URL')
REDIS_URL = environ.get('REDIS_URL')

# Primary Redis URL preference order: TLS URL > provider URL > generic URL
PRIMARY_REDIS_URL = REDIS_TLS_URL or REDISCLOUD_URL or REDIS_URL

# Backwards-compatible alias used in cache settings below
ALT_REDIS_URL = PRIMARY_REDIS_URL

# Connection/Pooling Notes
# ========================
# From testing each dyno seems to use, at a maximum, 8 connections for
# serving standard traffic. Channels seems to use 1 connection per dyno.
# Setting the connection pool could enforce limits to keep this under the
# maximum, however that just shifts the point of failure to the pool's max
# which is trickier to calibrate as it is traffic/dyno dependenent.
# It seems that connections are essentially per-process (so 5 per dyno;
# following the unicorn worker count) along with some left idle waiting to
# be closed (Heroku by default closes after 5 minutes)
# ========================
# The below config sets a more aggressive timeout but does not limit
# total connections — so the limit of 30 could be theoretically be hit if
# running 4 or so dynos. If this becomes a problem then we need to implement
# a pooling logic that ensures connections are shared amonst unicorn workers
# ========================

# Allow temporarily disabling strict TLS verification only when explicitly
# permitted via an environment variable (see note below). By default we keep
# verification enabled — do not leave the following enabled in production.
_INSECURE_REDIS = environ.get('INSECURE_REDIS', '') == '1'

CONNECTION_POOL_KWARGS = {}
if _INSECURE_REDIS:
    # WARNING: only use this flag temporarily for troubleshooting with
    # providers that use an unusual CA chain. Prefer fixing the provider's
    # certificate chain or adding the CA to the environment's trust store.
    CONNECTION_POOL_KWARGS = {"ssl_cert_reqs": None}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": ALT_REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Optional connection pool kwargs (only set when INSECURE_REDIS=1)
            **({"CONNECTION_POOL_KWARGS": CONNECTION_POOL_KWARGS} if CONNECTION_POOL_KWARGS else {}),
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 60,
        },
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
                # Use the same primary Redis URL; if it's rediss:// TLS is used
                "hosts": [{
                    "address": PRIMARY_REDIS_URL,
                    **({"ssl_cert_reqs": None} if _INSECURE_REDIS else {}),
                }],
            # Remove channels from groups after 3 hours
            # This matches websocket_timeout in Daphne
            "group_expiry": 10800,
        },
        # RedisChannelLayer should pool by default,
    },
}

# ==============================================================================
# Email / SendGrid
# ==============================================================================

if environ.get('EMAIL_HOST', ''):
    SERVER_EMAIL = environ['DEFAULT_FROM_EMAIL']
    DEFAULT_FROM_EMAIL = environ['DEFAULT_FROM_EMAIL']
    EMAIL_HOST = environ['EMAIL_HOST']
    EMAIL_HOST_USER = environ['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = environ['EMAIL_HOST_PASSWORD']
    EMAIL_PORT = int(environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'

elif environ.get('SENDGRID_API_KEY', ''):
    SERVER_EMAIL = environ.get('DEFAULT_FROM_EMAIL', 'root@localhost')
    DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL', 'notconfigured@NekoTabsite')
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = 'apikey'
    EMAIL_HOST_PASSWORD = environ['SENDGRID_API_KEY']
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True

elif environ.get('SENDGRID_USERNAME', ''):
    # These settings are deprecated as of NekoTab 2.6.0 (Ocicat).
    # When removing, also remove utils.mixins.WarnAboutLegacySendgridConfigVarsMixin and
    # templates/errors/legacy_sendgrid_warning.html (and references thereto).
    USING_LEGACY_SENDGRID_CONFIG_VARS = True
    SERVER_EMAIL = environ['SENDGRID_USERNAME']
    DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL', environ['SENDGRID_USERNAME'])
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = environ['SENDGRID_USERNAME']
    EMAIL_HOST_PASSWORD = environ['SENDGRID_PASSWORD']
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True

# ==============================================================================
# Sentry
# ==============================================================================

if not environ.get('DISABLE_SENTRY'):
    DISABLE_SENTRY = False
    sentry_sdk.init(
        dsn="https://6bf2099f349542f4b9baf73ca9789597@o85113.ingest.sentry.io/185382",
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(event_level=logging.WARNING),
            RedisIntegration(),
        ],
        send_default_pii=True,
        release=NekoTab_VERSION,
    )
