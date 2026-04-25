import logging
from os import environ

import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .core import TABBYCAT_VERSION

# ==============================================================================
# DigitalOcean production settings
# Activated by ON_DIGITALOCEAN=1 in the container environment.
# PostgreSQL  → self-hosted in Docker on the Droplet (no SSL required)
# Redis       → self-hosted in Docker on the Droplet (no TLS required)
# HTTPS       → Terminated at the DO Load Balancer; nginx proxies HTTP internally.
# ==============================================================================

if environ.get('TAB_DIRECTOR_EMAIL', ''):
    TAB_DIRECTOR_EMAIL = environ.get('TAB_DIRECTOR_EMAIL')

if environ.get('DJANGO_SECRET_KEY', ''):
    SECRET_KEY = environ.get('DJANGO_SECRET_KEY')

# Allow all *.nekotab.app subdomains, localhost for health checks, and any
# extra hosts passed via ALLOWED_HOSTS (e.g., the Droplet's raw IP during staging).
# Note: 'localhost:8000' needed because docker healthcheck sends Host: localhost:8000
_default_hosts = '.nekotab.app,localhost,localhost:8000,127.0.0.1,127.0.0.1:8000'
ALLOWED_HOSTS = environ.get('ALLOWED_HOSTS', _default_hosts).split(',')

# The DO Load Balancer terminates TLS and forwards HTTP to nginx on the Droplet.
# It sets X-Forwarded-Proto: https so Django knows the original request was HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Enforce HTTPS in production.
# Set DISABLE_HTTPS_REDIRECTS=disable for initial staging smoke-tests without LB.
if environ.get('DISABLE_HTTPS_REDIRECTS', '') != 'disable':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Exempt the internal health check path from the HTTPS redirect so that:
#  - docker-compose healthcheck (curl http://localhost:8000/health/) returns 200, not 301
#  - The DO Load Balancer /health/ probe works without TLS
SECURE_REDIRECT_EXEMPT = [r'^health/$']

# ==============================================================================
# Postgres (DigitalOcean Managed Database)
# ==============================================================================

try:
    _db_conn_max_age = int(environ.get('DB_CONN_MAX_AGE', '60'))
except ValueError:
    _db_conn_max_age = 60

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://nekotab:password@db:5432/nekotab',
        conn_max_age=_db_conn_max_age,
        # ssl_require=False: local Docker Postgres doesn't use SSL.
        # If you switch to a managed external DB, set DATABASE_URL with
        # ?sslmode=require and set ssl_require=True here.
        ssl_require=False,
    ),
}

# ==============================================================================
# Redis / Valkey  (DigitalOcean Managed Cache)
# DO Managed Valkey provides a rediss:// (TLS) connection string.
# ssl_cert_reqs=None allows DO's self-signed cluster cert.
# ==============================================================================

_redis_url = environ.get('REDIS_URL', 'redis://localhost:6379')

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": _redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 60,
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": None,
            },
        },
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [{
                "address": _redis_url,
                "ssl_cert_reqs": None,
            }],
            # Remove channels from groups after 3 hours
            "group_expiry": 10800,
        },
    },
}

# ==============================================================================
# Email
# DO blocks SMTP ports 25/465/587 on Droplets — use a third-party provider.
# Supported: generic SMTP (EMAIL_HOST) or SendGrid API key (SENDGRID_API_KEY).
# ==============================================================================

if environ.get('EMAIL_HOST', ''):
    _default_from = environ.get('DEFAULT_FROM_EMAIL', 'NekoTab Team <support@nekotab.app>')
    DEFAULT_FROM_EMAIL = _default_from
    SERVER_EMAIL = environ.get('SERVER_EMAIL', _default_from)
    REPLY_TO_EMAIL = environ.get('REPLY_TO_EMAIL', DEFAULT_FROM_EMAIL)
    EMAIL_HOST = environ['EMAIL_HOST']
    EMAIL_HOST_USER = environ['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = environ['EMAIL_HOST_PASSWORD']
    EMAIL_PORT = int(environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_TIMEOUT = int(environ.get('EMAIL_TIMEOUT', 20))

elif environ.get('SENDGRID_API_KEY', ''):
    _default_from = environ.get('DEFAULT_FROM_EMAIL', 'NekoTab Team <support@nekotab.app>')
    DEFAULT_FROM_EMAIL = _default_from
    SERVER_EMAIL = environ.get('SERVER_EMAIL', _default_from)
    REPLY_TO_EMAIL = environ.get('REPLY_TO_EMAIL', DEFAULT_FROM_EMAIL)
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = 'apikey'
    EMAIL_HOST_PASSWORD = environ['SENDGRID_API_KEY']
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_TIMEOUT = int(environ.get('EMAIL_TIMEOUT', 20))

else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL', 'NekoTab Team <support@nekotab.app>')
    SERVER_EMAIL = environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)
    REPLY_TO_EMAIL = environ.get('REPLY_TO_EMAIL', 'NekoTab Team <support@nekotab.app>')

# ==============================================================================
# Subdomain routing
# ==============================================================================

SUBDOMAIN_TOURNAMENTS_ENABLED = environ.get('SUBDOMAIN_TOURNAMENTS_ENABLED', 'true').lower() == 'true'
SUBDOMAIN_BASE_DOMAIN = environ.get('SUBDOMAIN_BASE_DOMAIN', 'nekotab.app')
RESERVED_SUBDOMAINS = environ.get('RESERVED_SUBDOMAINS', 'www,admin,api,jet,database,static,media').split(',')
ORGANIZATION_WORKSPACES_ENABLED = environ.get('ORGANIZATION_WORKSPACES_ENABLED', 'false').lower() == 'true'

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
# Sentry
# ==============================================================================

_sentry_dsn = environ.get('SENTRY_DSN')
if not environ.get('DISABLE_SENTRY') and _sentry_dsn:
    DISABLE_SENTRY = False
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(event_level=logging.WARNING),
            RedisIntegration(),
        ],
        send_default_pii=False,
        release=TABBYCAT_VERSION,
    )
