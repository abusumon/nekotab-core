from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from . import workspace_views

app_name = 'workspace'
handler404 = workspace_views.workspace_page_not_found

urlpatterns = [
    # Workspace pages
    path('', workspace_views.WorkspaceDashboardView.as_view(), name='dashboard'),
    path('tournaments/', workspace_views.TournamentListView.as_view(), name='tournament-list'),
    path('tournaments/new/', workspace_views.TournamentCreateView.as_view(), name='tournament-create'),
    path('members/', workspace_views.MembersView.as_view(), name='members'),
    path('settings/', workspace_views.SettingsView.as_view(), name='settings'),
    path('archive/', workspace_views.ArchiveView.as_view(), name='archive'),

    # Nested tournament access — delegates to existing tournament URL patterns
    path('tournaments/<slug:tournament_slug>/', include('tournaments.urls')),

    # System routes that must work on org subdomains
    path('accounts/', include('users.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(domain="djangojs"), name='javascript-catalog'),
    path('api/', include('api.urls')),

    # Organization management (needed by nav template's {% url 'org-list' %})
    path('organizations/', include('organizations.urls')),

    # Admin / utility routes
    path('database/', admin.site.urls),
    path('jet/', include('jet.urls', 'jet')),
    path('summernote/', include('django_summernote.urls')),
]
