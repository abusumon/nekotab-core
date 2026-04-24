from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import include, path
from django.utils.translation import gettext as _
from django.views.i18n import JavaScriptCatalog
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

import tournaments.views
from importer.views import LoadDemoView
from participant_crm.views import UnsubscribeView as CrmUnsubscribeView
from organizations import views as organizations_views
from users.views import BlankSiteStartView
from sitemaps import StaticViewSitemap, TournamentSitemap, MotionBankSitemap
from content.sitemaps import LearnArticleSitemap, TrustPagesSitemap

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

    # Indices
    path('',

        tournaments.views.PublicSiteIndexView.as_view(),
        name='tabbycat-index'),
    path('start/',
        BlankSiteStartView.as_view(),
        name='blank-site-start'),
    path('create/',
        tournaments.views.CreateTournamentView.as_view(),
        name='tournament-create'),
    path('create/ie/',
        tournaments.views.CreateIETournamentView.as_view(),
        name='ie-tournament-create'),
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

    # SEO: Sitemap and robots
    path('sitemap.xml',
        sitemap,
        {'sitemaps': {
            'static': StaticViewSitemap,
            'tournaments': TournamentSitemap,
            'motions': MotionBankSitemap,
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
        admin.site.urls),

    # Accounts
    path('accounts/', include('users.urls')),

    # Social auth (Google OAuth etc.)
    path('accounts/', include('allauth.urls')),

    # Notifications
    path('notifications/',
        include('notifications.urls')),

    # Email Campaigns (superuser only)
    path('campaigns/',
        include('campaigns.urls')),

    # CRM unsubscribe (public)
    path('unsubscribe/',
        CrmUnsubscribeView.as_view(),
        name='crm-unsubscribe'),

    # Admin Analytics Dashboard (superuser only)
    path('analytics/',
        include('analytics.urls')),

    # Organizations (multi-tenant)
    path('organizations/',
        include('organizations.urls')),

    # API
    path('api/',
        include('api.urls')),

    # Archive import/export
    path('archive/',
        include('importer.urls_archive')),

    # Global Debate Forum
    path('forum/',
        include('forum.urls')),

    # Global Motion Bank
    path('motions-bank/',
        include('motionbank.urls')),

    # Global Debate Passport
    path('passport/',
        include('passport.urls')),

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

    # Tournament URLs
    path('<slug:tournament_slug>/',
        include('tournaments.urls')),

    # Tournament Chat Rooms
    path('<slug:tournament_slug>/chat/', include('chat.urls')),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:  # Only serve debug toolbar when on DEBUG
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))


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
