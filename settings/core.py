import os

from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _


def _env_bool(name, default=False):
    """Parse a boolean environment variable.  Accepts 1/0, true/false, yes/no (case-insensitive)."""
    val = os.environ.get(name, '')
    if not val:
        return default
    return val.strip().lower() in ('1', 'true', 'yes')


BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==============================================================================
# Overwritten in local.py or heroku.py
# ==============================================================================

ADMINS = ('NekoTab', 'contact@nekotab.app'),
MANAGERS = ADMINS
DEBUG = _env_bool('DEBUG')
ENABLE_DEBUG_TOOLBAR = False # Must default to false; overriden in Dev config
DISABLE_SENTRY = True # Overriden in Heroku config

# SECRET_KEY must be provided via environment variable in all environments.
# local.py generates a random key for development; production configs
# (heroku.py, render.py) read DJANGO_SECRET_KEY from the environment.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY and not os.environ.get('LOCAL_SETTINGS', ''):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable is required. "
        "Set it in your environment or use local.py for development."
    )

# nekospeech API URL (for the separate Heroku app).
# Defaults to '/api/ie' for local / same-origin deployments.
NEKOSPEECH_URL = os.environ.get('NEKOSPEECH_URL', '/api/ie')

# IE API Key — must match NEKOSPEECH_IE_API_KEY on the nekospeech Heroku app
NEKOSPEECH_IE_API_KEY = os.environ.get('NEKOSPEECH_IE_API_KEY', '')

# nekocongress frontend URL for Vue components.  Empty string means Vue
# uses same-origin relative paths through the nginx /api/congress/ proxy.
# Only set this if you want Vue to call the congress API directly (cross-origin).
NEKOCONGRESS_URL = os.environ.get('NEKOCONGRESS_URL', '')
NEKOCONGRESS_API_KEY = os.environ.get('NEKOCONGRESS_API_KEY', '')

# ==============================================================================
# Version
# ==============================================================================

NekoTab_VERSION = '2.10.0'
TABBYCAT_VERSION = '2.10.0'
NekoTab_CODENAME = 'Sphynx'
TABBYCAT_CODENAME = 'Sphynx'
READTHEDOCS_VERSION = 'v2.10.0'

# ==============================================================================
# Internationalization and Localization
# ==============================================================================

USE_I18N = True
USE_TZ = True
LANGUAGE_CODE = 'en'
TIME_ZONE = os.environ.get('TIME_ZONE', 'Australia/Melbourne')

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Add custom languages not provided by Django
EXTRA_LANG_INFO = {
    'tzl': {
        # Use code for Talossan; can't use proper reserved code...
        # Talossan is a constructed language, without native speakers,
        # so the odds of having a translation are low.
        'code': 'tzl',
        'name': 'Translation',
        'name_local': 'Translation',
    },
}

# Languages that should be available in the switcher
import django.conf.locale
LANG_INFO = dict(django.conf.locale.LANG_INFO, **EXTRA_LANG_INFO)
django.conf.locale.LANG_INFO = LANG_INFO

LANGUAGES = [
    ('ar', _('Arabic')),
    ('ast', _('Asturian')),
    ('bn', _('Bengali')),
    ('bg', _('Bulgarian')),
    ('ca', _('Catalan')),
    ('cs', _('Czech')),
    ('de', _('German')),
    ('en', _('English')),
    ('es', _('Spanish')),
    ('fr', _('French')),
    ('he', _('Hebrew')),
    ('hi', _('Hindi')),
    ('id', _('Indonesian')),
    ('it', _('Italian')),
    ('ja', _('Japanese')),
    ('kk', _('Kazakh')),
    ('ms', _('Malay')),
    ('pt', _('Portuguese')),
    ('ro', _('Romanian')),
    ('ru', _('Russian')),
    ('tr', _('Turkish')),
    ('vi', _('Vietnamese')),
    ('zh-hans', _('Simplified Chinese')),
    ('tzl', _('Translation')),
]

STATICI18N_ROOT = os.path.join(BASE_DIR, "locale")

FORMAT_MODULE_PATH = [
    'utils.formats',
]

# ==============================================================================
# Django-specific Modules
# ==============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # User language preferences; must be after Session
    'django.middleware.locale.LocaleMiddleware',
    # Set Etags; i.e. cached requests not on network; must precede Common
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Must be after SessionMiddleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    # Rewrite subdomain requests to slug-based paths (feature gated)
    'utils.middleware.SubdomainTenantMiddleware',
    'utils.middleware.DebateMiddleware',
    # 404 diagnostic logging
    'utils.middleware_404.Log404Middleware',
    # Redirect fallback: serves django.contrib.redirects entries
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    # Analytics tracking middleware
    'analytics.middleware.AnalyticsMiddleware',
]

TABBYCAT_APPS = (
    'core',
    'actionlog',
    'adjallocation',
    'adjfeedback',
    'analytics',
    'api',
    'availability',
    'breakqual',
    'campaigns',
    'checkins',
    'divisions', # obsolete
    'draw',
    'motions',
    'options',
    'organizations',
    'participants',
    'printing',
    'privateurls',
    'results',
    'retention',
    'tournaments',
    'venues',
    'utils',
    'users',
    'standings',
    'notifications',
    'importer',
    'registration',
    'forum',
    'motionbank',
    'passport',
    'content',
    'speech_events',
    'congress_events',
    'participant_crm',
)

INSTALLED_APPS = (
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'daphne',
    'jet',
    'utils.admin_site.NekoTabAdminConfig',  # custom admin site (replaces 'django.contrib.admin')
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.redirects',
    'axes',
    'channels', # For Websockets / real-time connections (above whitenoise)
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_summernote',  # Keep above our apps; as we unregister an admin model
    'django.contrib.messages') \
    + TABBYCAT_APPS + (
    'dynamic_preferences',
    'django_extensions',  # For Secret Generation Command
    'gfklookupwidget',
    'formtools',
    'statici18n', # Compile js translations as static file; saving requests
    'polymorphic',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'django_better_admin_arrayfield',
)

ROOT_URLCONF = 'urls'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
FIXTURE_DIRS = (os.path.join(os.path.dirname(BASE_DIR), 'data', 'fixtures'), )
SILENCED_SYSTEM_CHECKS = ('urls.W002',)

# ==============================================================================
# Templates
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',  # for Jet
                'utils.context_processors.debate_context',  # for tournament config vars
                'dynamic_preferences.processors.global_preferences',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        }
    },
]

# ==============================================================================
# Caching
# ==============================================================================

PUBLIC_FAST_CACHE_TIMEOUT = int(os.environ.get('PUBLIC_FAST_CACHE_TIMEOUT', 60 * 1))
PUBLIC_SLOW_CACHE_TIMEOUT = int(os.environ.get('PUBLIC_SLOW_CACHE_TIMEOUT', 60 * 3.5))
TAB_PAGES_CACHE_TIMEOUT = int(os.environ.get('TAB_PAGES_CACHE_TIMEOUT', 60 * 120))

# Default non-heroku cache is to use local memory
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# ==============================================================================
# Static Files and Compilation
# ==============================================================================

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'locale'),  # django-statici18n jsi18n compiled JS
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ==============================================================================
# Logging
# ==============================================================================

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'sentry.errors': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        },
    },
}

for app in TABBYCAT_APPS:
    LOGGING['loggers'][app] = {
        'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
    }

# 404 diagnostic logger — routes to console (visible in Heroku logs)
LOGGING['loggers']['nekotab.404'] = {
    'handlers': ['console'],
    'level': 'WARNING',
    'propagate': False,
}

# Required by django.contrib.redirects
SITE_ID = 1

# ==============================================================================
# Messages
# ==============================================================================

MESSAGE_TAGS = {messages.ERROR: 'danger', }

# ==============================================================================
# Summernote (WYSWIG)
# ==============================================================================

SUMMERNOTE_THEME = 'bs4' # Bootstrap 4

SUMMERNOTE_CONFIG = {
    'width': '100%',
    'height': '480',
    'toolbar': [
        ['style', ['bold', 'italic', 'underline', 'fontsize', 'color', 'clear']],
        ['para', ['ul', 'ol']],
        ['insert', ['link', 'picture']],
        ['misc', ['undo', 'redo', 'codeview']],
    ],
    'disable_upload': True,
    'iframe': True, # Necessary; if just to compartmentalise jQuery dependency,
}

X_FRAME_OPTIONS = 'SAMEORIGIN' # Necessary to get Django-Summernote working because of Django 3 changes

# ==============================================================================
# Database
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# ==============================================================================
# Channels
# ==============================================================================

ASGI_APPLICATION = "asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ==============================================================================
# Dynamic preferences
# ==============================================================================

DYNAMIC_PREFERENCES = {
    'REGISTRY_MODULE': 'preferences',
}

# ==============================================================================
# REST Framework
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('API_THROTTLE_ANON', '60/minute'),
        'user': os.environ.get('API_THROTTLE_USER', '300/minute'),
    },
    'DEFAULT_PAGINATION_CLASS': 'drf_link_header_pagination.LinkHeaderLimitOffsetPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'NekoTab API',
    'DESCRIPTION': 'Parliamentary debate tabulation software',
    'VERSION': '1.3.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'api/v\d+',
    'CONTACT': {'name': 'NekoTab', 'email': 'contact@nekotab.app'},
    'LICENSE': {'name': 'AGPL 3', 'url': 'https://www.gnu.org/licenses/agpl-3.0.en.html'},
    'EXTENSIONS_INFO': {
        "x-logo": {
            "url": "/static/logo.svg",
            "altText": "NekoTab logo",
        },
    }
}

# ----------------------------------------
# CORS-related settings for REST framework
# ----------------------------------------

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in
    os.environ.get('CORS_ALLOWED_ORIGINS', 'https://nekotab.app,https://www.nekotab.app').split(',')
    if o.strip()
]
CORS_URLS_REGEX = r'^/api(/.*)?$'

# ==============================================================================
# Security headers
# ==============================================================================

SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ==============================================================================
# Password validators
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication backends
# The TournamentAdminBackend grants admin model permissions to tournament
# owners and org OWNER/ADMIN users so they can use the /database/ editor.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'utils.admin_site.TournamentAdminBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# django-allauth configuration
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'  # We handle verification in users.views
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

# Google OAuth → existing account auto-connection
# Google verifies emails before issuing OAuth tokens, so trusting Google's
# email for account matching is safe. These settings allow a Google login to
# automatically connect to an existing NekoTab account with the same email
# instead of showing the social-account signup form.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_AUTO_CONNECT_BY_EMAIL = True

# ==============================================================================
# Subdomain routing (defaults; can be overridden in env-specific settings)
# ==============================================================================

# Disabled by default; enable in environment settings (e.g., heroku.py)
SUBDOMAIN_TOURNAMENTS_ENABLED = _env_bool('SUBDOMAIN_TOURNAMENTS_ENABLED')
SUBDOMAIN_BASE_DOMAIN = os.environ.get('SUBDOMAIN_BASE_DOMAIN', '')
RESERVED_SUBDOMAINS = os.environ.get(
    'RESERVED_SUBDOMAINS', 'www,admin,api,jet,database,static,media'
).split(',')

# Organization workspace routing; when False, SubdomainTenantMiddleware
# behaves identically to the old SubdomainTournamentMiddleware.
ORGANIZATION_WORKSPACES_ENABLED = _env_bool('ORGANIZATION_WORKSPACES_ENABLED')

# Cross-subdomain session/CSRF cookies: when a base domain is configured,
# set the cookie domain to the parent domain so that a session created at
# nekotab.app is also valid at orgslug.nekotab.app.
# Production configs (heroku.py) may override these with stricter settings.
if SUBDOMAIN_BASE_DOMAIN:
    SESSION_COOKIE_DOMAIN = f".{SUBDOMAIN_BASE_DOMAIN}"
    CSRF_COOKIE_DOMAIN = f".{SUBDOMAIN_BASE_DOMAIN}"

# ==============================================================================
# Email (defaults; can be overridden in environment-specific settings)
# ==============================================================================

# Default from email for outbound messages; include display name for branding
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'NekoTab Team <support@nekotab.app>')

# Server email for error emails; default to from email
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Comma-separated list of admin notification emails for operational alerts
_admin_emails = os.environ.get('ADMIN_NOTIFICATION_EMAILS', '').strip()
ADMIN_NOTIFICATION_EMAILS = [e.strip() for e in _admin_emails.split(',') if e.strip()] if _admin_emails else []

# Optional Reply-To header for outbound emails
REPLY_TO_EMAIL = os.environ.get('REPLY_TO_EMAIL', 'NekoTab Team <support@nekotab.app>')

# ==============================================================================
# AdSense / Monetization
# ==============================================================================

ADSENSE_ENABLED = _env_bool('ADSENSE_ENABLED', default=True)
ADSENSE_PUBLISHER_ID = os.environ.get('ADSENSE_PUBLISHER_ID', 'ca-pub-4135779137186219')
ADSENSE_SLOT_CONTENT = os.environ.get('ADSENSE_SLOT_CONTENT', '7630939625')
ADSENSE_SLOT_FOOTER = os.environ.get('ADSENSE_SLOT_FOOTER', '7630939625')
ADSENSE_SLOT_TABLE = os.environ.get('ADSENSE_SLOT_TABLE', '7630939625')

# ==============================================================================
# SEO / Canonical
# ==============================================================================

# Public site base URL for canonical tags and sitemap domain hints
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'https://nekotab.app').rstrip('/')

# ==============================================================================
# Tournament Retention / Auto-cleanup
# ==============================================================================

# Number of days after creation before a tournament becomes eligible for
# automatic deletion.  Set to 0 to disable retention enforcement.
TOURNAMENT_RETENTION_DAYS = int(os.environ.get('TOURNAMENT_RETENTION_DAYS', '0'))

# DELETE_ONLY  — delete without exporting
# EXPORT_THEN_DELETE — export archive first, then delete
TOURNAMENT_RETENTION_MODE = os.environ.get('TOURNAMENT_RETENTION_MODE', 'EXPORT_THEN_DELETE')

# CSV  — multi-CSV zip archive  (default, no external deps)
# JSON — single structured JSON file
TOURNAMENT_EXPORT_FORMAT = os.environ.get('TOURNAMENT_EXPORT_FORMAT', 'CSV')

# LOCAL_MEDIA   — save to MEDIA_ROOT/archives/
# S3_COMPATIBLE — use boto3 + env vars (AWS_ACCESS_KEY_ID, etc.)
TOURNAMENT_EXPORT_STORAGE = os.environ.get('TOURNAMENT_EXPORT_STORAGE', 'LOCAL_MEDIA')

# Grace period in hours before a scheduled tournament is actually deleted.
TOURNAMENT_RETENTION_GRACE_HOURS = int(os.environ.get('TOURNAMENT_RETENTION_GRACE_HOURS', '24'))

# Comma-separated list of extra emails to notify about deletions (in addition
# to the tournament owner).
_notify_raw = os.environ.get('TOURNAMENT_EXPORT_NOTIFY_EMAILS', '').strip()
TOURNAMENT_EXPORT_NOTIFY_EMAILS = [e.strip() for e in _notify_raw.split(',') if e.strip()] if _notify_raw else []

# S3-compatible storage settings (only used when TOURNAMENT_EXPORT_STORAGE == 'S3_COMPATIBLE')
TOURNAMENT_EXPORT_S3_BUCKET = os.environ.get('TOURNAMENT_EXPORT_S3_BUCKET', '')
TOURNAMENT_EXPORT_S3_ENDPOINT = os.environ.get('TOURNAMENT_EXPORT_S3_ENDPOINT', '')
TOURNAMENT_EXPORT_S3_REGION = os.environ.get('TOURNAMENT_EXPORT_S3_REGION', 'auto')

# ==============================================================================
# Brute-Force Protection (django-axes)
# ==============================================================================

AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = 1                 # 1-hour lockout
AXES_LOCKOUT_PARAMETERS = [['ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_VERBOSE = False
