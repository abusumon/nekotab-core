from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.templatetags.static import static
from django.urls import include, path
from django.utils.translation import gettext as _
from django.views.i18n import JavaScriptCatalog
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView, TemplateView
from django.views.decorators.cache import cache_page
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenBlacklistView,
)
from organizations.api.views import OrgTokenObtainPairView

import tournaments.views
from importer.views import LoadDemoView
from participant_crm.views import UnsubscribeView as CrmUnsubscribeView
from organizations import views as organizations_views
from users.views import BlankSiteStartView, GoogleOAuthLoginGuardView, UserDashboardView
from sitemaps import StaticViewSitemap, TournamentSitemap, MotionBankSitemap, TicketEventSitemap
from content.sitemaps import LearnArticleSitemap, TrustPagesSitemap
import motionbank.views as motionbank_views
from campaigns.views import serve_image
from content.views import ContactForumView
from donations import views as donations_views

def _ready_view(request):
    from django.db import connection
    connection.ensure_connection()
    return JsonResponse({'status': 'ready', 'db': 'ok'})


# ==============================================================================
# Base Patterns
# ==============================================================================

urlpatterns = [

    # Health check — used by the DO Load Balancer and docker-compose healthcheck.
    # Returns 200 quickly; nginx also has its own /health/ for LB probes, but
    # this endpoint confirms Django itself (+ DB via previous migrations) is up.
    path('health/',
        lambda request: HttpResponse('ok', content_type='text/plain'),
        name='health-check'),

    # Readiness probe — verifies DB connectivity before accepting traffic.
    path('ready/', _ready_view, name='ready-check'),

    # Indices
    path('',

        tournaments.views.PublicSiteIndexView.as_view(),
        name='tabbycat-index'),
    path('me/',
        UserDashboardView.as_view(),
        name='user-dashboard'),
    path('start/',
        BlankSiteStartView.as_view(),
        name='blank-site-start'),
    path('create/',
        tournaments.views.CreateTournamentView.as_view(),
        name='tournament-create'),
    path('tournament/<int:pk>/delete/',
        tournaments.views.TournamentDeleteConfirmView.as_view(),
        name='tournament-delete-confirm'),
    path('support/', include('support.urls', namespace='support')),
    # Alias matching the URL other tab platforms use, so a link shared as
    # "nekotab.app/tournaments/new/" lands somewhere real.
    path('tournaments/new/',
        RedirectView.as_view(pattern_name='tournament-create', permanent=False),
        name='tournament-new'),
    # POST only — a GET here would be fired by prefetchers and crawlers, and
    # each one would create a tournament.
    path('create/demo/',
        tournaments.views.CreateDemoTournamentView.as_view(),
        name='tournament-create-demo'),
    path('create/congress/',
        tournaments.views.CreateCongressTournamentView.as_view(),
        name='congress-tournament-create'),
    path('load-demo/',
        LoadDemoView.as_view(),
        name='load-demo'),

    # Claim unassigned tournament ownership (admin/superuser use primarily)
    path('claim/<slug:slug>/',
        tournaments.views.ClaimTournamentOwnershipView.as_view(),
        name='tournament-claim'),

    # Top Level Pages
    path('style/',
        tournaments.views.StyleGuideView.as_view(),
        name='style-guide'),

    # Set language override
    path('i18n/',
        include('django.conf.urls.i18n')),

    # JS Translations Catalogue; includes all djangojs files in locale folders
    path('jsi18n/',
         JavaScriptCatalog.as_view(domain="djangojs"),
         name='javascript-catalog'),

    # Google Search Console verification files
    path('googlee0a2b1e83278e880.html',
        TemplateView.as_view(template_name='verification/googlee0a2b1e83278e880.html')),
    path('google4a7d5456478d704b.html',
        TemplateView.as_view(template_name='verification/google4a7d5456478d704b.html')),

    path('favicon.ico',
        RedirectView.as_view(url=static('favicon.ico'), permanent=True),
        name='favicon-redirect'),

    # SEO: Sitemap and robots
    path('sitemap.xml',
        sitemap,
        {'sitemaps': {
            'static': StaticViewSitemap,
            'tournaments': TournamentSitemap,
            'motions': MotionBankSitemap,
            'events': TicketEventSitemap,
            'articles': LearnArticleSitemap,
            'trust': TrustPagesSitemap,
        }},
        name='sitemap'),
    path('robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name='robots-txt'),
    path('ads.txt',
        TemplateView.as_view(template_name='ads.txt', content_type='text/plain'),
        name='ads-txt'),

    # Summernote (WYSYWIG)
    path('summernote/',
        include('django_summernote.urls')),

    # Admin area
    path('jet/',
        include('jet.urls', 'jet')),
    path('jet/dashboard/',
        lambda request: HttpResponseRedirect('/database/'),
        name='jet-dashboard-redirect'),
    path('database/',
        admin.site.urls),
    path('admin/',
        RedirectView.as_view(url='/database/', permanent=False),
        name='admin-shortcut'),

    # Accounts
    path('accounts/', include('users.urls')),

    # Social auth (Google OAuth etc.)
    path('accounts/google/login/',
        GoogleOAuthLoginGuardView.as_view(),
        name='google-login-guard'),
    path('accounts/', include('allauth.urls')),

    # Explicit login shortcut so /login/ never falls through to tournament slug routes
    path('login/',
        RedirectView.as_view(pattern_name='login', permanent=False),
        name='login-shortcut'),

    # Notifications
    path('notifications/',
        include('notifications.urls')),

    # Email Campaigns (superuser only)
    path('campaigns/',
        include('campaigns.urls')),

    # Donations (Lemon Squeezy webhook)
    path('donations/',
        include('donations.urls')),

    # NekoTab Premium — the $5 per-tournament unlock.
    #
    # Top-level rather than under /donations/ because it is the page the
    # paywall sends people to and the URL a director reads off an email; it
    # also has to sit outside every tournament-scoped route so subdomain
    # rewriting leaves it alone (see SubdomainTenantMiddleware.BAD_PREFIXES).
    path('premium/<int:tournament_id>/',
        donations_views.TournamentPremiumView.as_view(),
        name='premium-purchase'),
    path('premium/<int:tournament_id>/status/',
        donations_views.PremiumStatusView.as_view(),
        name='premium-status'),
    path('premium/<int:tournament_id>/redeem/',
        donations_views.RedeemPromoCodeView.as_view(),
        name='premium-redeem'),
    # Manual bKash flow. Top-level and memorable because it is linked from the
    # home page nav and read out in support replies.
    path('bkash/',
        donations_views.BkashPaymentRequestView.as_view(),
        name='bkash'),
    path('pricing/',
        tournaments.views.PricingView.as_view(),
        name='pricing'),

    # CRM unsubscribe (public)
    path('unsubscribe/',
        CrmUnsubscribeView.as_view(),
        name='crm-unsubscribe'),

    # Admin Analytics Dashboard (superuser only)
    path('analytics/',
        include('analytics.urls')),

    # NOTE: the public event-discovery route (`events/` ->
    # organizations.views.PublicEventDiscoverView, name 'org-event-discover')
    # is deliberately not here yet.
    #
    # This URLconf lives in the public submodule; that view lives in the private
    # parent repo, and it is still in progress there. Landing the route without
    # the view made Django's system check fail at container start — which meant
    # `migrate` never ran and the deploy died on 2026-07-26. Add this back in the
    # same change that lands PublicEventDiscoverView, not before.

    # Organizations (multi-tenant)
    path('organizations/',
        include('organizations.urls')),

    # Event Ticketing — public-facing (hub.nekotab.app/tickets/...)
    path('tickets/', include('tickets.urls_public', namespace='tickets')),

    # Event Ticketing API
    path('api/tickets/', include('tickets.urls_api')),

        # API
    path('api/',
        include('api.urls')),

    # JWT Authentication endpoints — uses OrgTokenObtainPairView to inject org claims
    path('api/v1/auth/token/',
        OrgTokenObtainPairView.as_view(),
        name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'),
    path('api/v1/auth/logout/',
        TokenBlacklistView.as_view(),
        name='token_blacklist'),

    # Archive import/export
    path('archive/',
        include('importer.urls_archive')),

    # Public tool pages (no tournament context required). /tools/ itself needs
    # an index: the sub-paths existed but the parent 404'd, so the one URL people
    # actually guess and link to led nowhere.
    path('tools/',
        TemplateView.as_view(template_name='pages/tools_index.html'),
        name='tools-index'),
    path('tools/import/',
        include('importer.urls_tool')),
    path('tools/analyze/',
        include('analyzer.urls')),

    # Contact Us. Lives at /contact/ — the URL people guess and the one the
    # home page and footer link to. /forum/ is the original path and stays as
    # a permanent redirect so older links and search results still work.
    path('contact/',
        ContactForumView.as_view(),
        name='contact'),
    path('forum/',
        RedirectView.as_view(pattern_name='contact', permanent=True),
        name='contact-forum'),

    # Global Motion Bank — flat-file edition at /motions/
    path('motions/',
        motionbank_views.MotionsPageView.as_view(),
        name='motions'),
    path('motions/api/',
        motionbank_views.MotionsAPIView.as_view(),
        name='motions-api'),

    # Global Motion Bank (legacy DB-backed) at /motions-bank/
    path('motions-bank/',
        include('motionbank.urls')),

        # Workspace React SPA — served via Django template
    path('workspace/', TemplateView.as_view(template_name='frontend/index.html'), name='workspace-index'),
    path('workspace/<path:path>', TemplateView.as_view(template_name='frontend/index.html'), name='workspace-catchall'),

    # Content: Learn hub + Trust/Legal pages
    path('', include('content.urls')),

    # Retention archive downloads
    path('', include('retention.urls')),

    # Marketing pages
    path('for-organizers/',
        TemplateView.as_view(template_name='marketing/for_organizers.html'),
        name='for-organizers'),

    # Registration flows
    path('register/tournament/',
        tournaments.views.RegisterTournamentView.as_view(),
        name='register-tournament'),
    path('register/organization/',
        organizations_views.RegisterOrganizationView.as_view(),
        name='register-organization'),

    # Donation / Support page
    path('donate/',
        TemplateView.as_view(template_name='pages/donate.html'),
        name='donate'),

    # SEO landing pages
    path('free-debate-tab-software/',
        TemplateView.as_view(template_name='pages/free-debate-tab-software.html'),
        name='seo-free-tab'),
    path('bp-debate-tabulation/',
        TemplateView.as_view(template_name='pages/bp-debate-tabulation.html'),
        name='seo-bp-tab'),
    path('tabroom-alternative/',
        TemplateView.as_view(template_name='pages/tabroom-alternative.html'),
        name='seo-tabroom-alt'),
    path('calicotab-alternative/',
        TemplateView.as_view(template_name='pages/calicotab-alternative.html'),
        name='seo-calicotab-alt'),
    path('debate-data-alternative/',
        TemplateView.as_view(template_name='pages/debate-data-alternative.html'),
        name='seo-debatedata-alt'),
    path('congress-debate-tabulation/',
        TemplateView.as_view(template_name='pages/congress-debate-tabulation.html'),
        name='seo-congress-tab'),
    path('debate-motions/',
        cache_page(60)(
            TemplateView.as_view(
                template_name='pages/debate-motions.html',
                extra_context={
                    'meta_description': 'Search real debate motions across BP, WSDC, Public Forum, Lincoln-Douglas, Policy and Asians/Australs, then jump into the full Motion Bank.',
                    'seo_keywords': 'debate motions, motion bank, BP motions, WSDC motions, public forum motions, lincoln douglas topics, policy debate resolutions',
                    'canonical_url': 'https://nekotab.app/debate-motions/',
                },
            )
        ),
        name='seo-debate-motions'),
    path('debate-topics/',
        TemplateView.as_view(
            template_name='pages/debate-topics.html',
            extra_context={
                'meta_description': 'Find debate topics for students and teams, then practice with real tournament motions across BP, WSDC, Public Forum, Lincoln-Douglas and Policy formats.',
                'seo_keywords': 'debate topics, debate topics for students, debate prep topics, debate practice topics, tournament debate topics',
                'canonical_url': 'https://nekotab.app/debate-topics/',
            },
        ),
        name='seo-debate-topics'),

    # Feature-specific SEO landing pages
    path('debate-motion-bank/',
        TemplateView.as_view(template_name='pages/debate-motion-bank.html'),
        name='seo-motion-bank'),
    path('debate-schedule-planner/',
        TemplateView.as_view(template_name='pages/debate-schedule-planner.html'),
        name='seo-schedule-planner'),
    path('debate-registration-forms/',
        TemplateView.as_view(template_name='pages/debate-registration-forms.html'),
        name='seo-debate-forms'),
    path('debate-website-builder/',
        TemplateView.as_view(template_name='pages/debate-website-builder.html'),
        name='seo-website-builder'),
    path('debate-ticketing/',
        TemplateView.as_view(template_name='pages/debate-ticketing.html'),
        name='seo-debate-ticketing'),

    # Tournament URLs
    path('<slug:tournament_slug>/',
        include('tournaments.urls')),

    # Tournament Chat Rooms
    path('<slug:tournament_slug>/chat/', include('chat.urls')),

    # Public image serve URL — no auth required; used in HTML emails
    path('uploads/<uuid:pk>/', serve_image, name='image-serve'),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:  # Only serve debug toolbar when on DEBUG
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))

# Serve uploaded media files in local/Docker development
if settings.DEBUG:
    from django.conf.urls.static import static as static_files
    urlpatterns += static_files(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# ==============================================================================
# Logout/Login Confirmations
# ==============================================================================

# These messages don't always work properly with unit tests, so set fail_silently=True

@receiver(user_logged_in)
def on_user_logged_in(sender, request, **kwargs):
    if not urlparse(request.META.get('HTTP_REFERER')).path == '/accounts/login/':
        # The message is extraneous when their account was just created
        return
    if kwargs.get('user'):
        messages.info(request,
            _("Hi, %(user)s — you just logged in!")  % {'user': kwargs['user'].username},
            fail_silently=True)
    else: # should never happen, but just in case
        messages.info(request, _("Welcome! You just logged in!"), fail_silently=True)
