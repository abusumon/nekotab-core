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
    path('tournaments/<slug:tournament_slug>/staff/', workspace_views.TournamentStaffView.as_view(), name='tournament-staff'),
    path('tournaments/<slug:tournament_slug>/staff/invite/', workspace_views.TournamentStaffInviteView.as_view(), name='tournament-staff-invite'),
    path('tournaments/staff-invitations/<uuid:token>/', workspace_views.TournamentStaffAcceptInvitationView.as_view(), name='tournament-staff-accept'),
    path('members/', workspace_views.MembersView.as_view(), name='members'),
    path('members/invite/', workspace_views.InviteMemberView.as_view(), name='invite-member'),
    path('accept-invitation/<uuid:token>/', workspace_views.AcceptInvitationView.as_view(), name='accept-invitation'),
    path('practice/', include('practice.urls')),
    path('rankings/', workspace_views.RankingsView.as_view(), name='rankings'),
    path('analytics/', workspace_views.AnalyticsView.as_view(), name='analytics'),
    path('settings/', workspace_views.SettingsView.as_view(), name='settings'),
    path('archive/', workspace_views.ArchiveView.as_view(), name='archive'),

    # Form builder
    path('forms/', workspace_views.FormListView.as_view(), name='form-list'),
    path('forms/new/', workspace_views.FormCreateView.as_view(), name='form-create'),
    path('forms/<slug:form_slug>/', workspace_views.FormBuilderView.as_view(), name='form-builder'),
    path('forms/<slug:form_slug>/responses/', workspace_views.FormResponseListView.as_view(), name='form-responses'),
    path('forms/<slug:form_slug>/confirm/<int:response_id>/', workspace_views.FormConfirmView.as_view(), name='form-confirm'),
    path('forms/<slug:form_slug>/unconfirm/<int:response_id>/', workspace_views.FormUnconfirmView.as_view(), name='form-unconfirm'),
    path('forms/<slug:form_slug>/delete-response/<int:response_id>/', workspace_views.FormDeleteResponseView.as_view(), name='form-delete-response'),
    path('forms/<slug:form_slug>/delete/', workspace_views.FormDeleteView.as_view(), name='form-delete'),
    path('forms/<slug:form_slug>/toggle/', workspace_views.FormToggleView.as_view(), name='form-toggle'),
    path('forms/<slug:form_slug>/submit/', workspace_views.PublicFormSubmissionView.as_view(), name='form-submit'),
    path('forms/<slug:form_slug>/confirmed/', workspace_views.PublicFormConfirmationBoardView.as_view(), name='form-confirmed'),

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
