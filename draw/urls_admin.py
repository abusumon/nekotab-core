from django.urls import include, path

from . import release_views, views

urlpatterns = [

    path('round/<int:round_seq>/', include([
        # Creation/Release
        path('',
            views.AdminDrawView.as_view(),
            name='draw'),
        path('create/',
            views.CreateDrawView.as_view(),
            name='draw-create'),
        path('details/',
            views.AdminDrawWithDetailsView.as_view(),
            name='draw-details'),
        path('position-balance/',
            views.PositionBalanceReportView.as_view(),
            name='draw-position-balance'),
        path('confirm/',
            views.ConfirmDrawCreationView.as_view(),
            name='draw-confirm'),
        path('regenerate/',
            views.ConfirmDrawRegenerationView.as_view(),
            name='draw-regenerate'),

        # Email
        path('email-adjudicators',
            views.EmailAdjudicatorAssignmentsView.as_view(),
            name='draw-adj-email'),
        path('email-debaters',
            views.EmailTeamAssignmentsView.as_view(),
            name='draw-team-email'),

        # Side and Matchup Editing
        path('edit/',
            views.EditDebateTeamsView.as_view(),
            name='edit-debate-teams'),

        # Display
        path('display/',
            views.AdminDrawDisplayView.as_view(),
            name='draw-display'),
        path('display-by-venue/',
            views.AdminDrawDisplayForSpecificRoundByVenueView.as_view(),
            name='draw-display-specific-round-by-venue'),
        path('display-by-team/',
            views.AdminDrawDisplayForSpecificRoundByTeamView.as_view(),
            name='draw-display-specific-round-by-team'),
        path('release/',
            views.DrawReleaseView.as_view(),
            name='draw-release'),
        path('unrelease/',
            views.DrawUnreleaseView.as_view(),
            name='draw-unrelease'),

        # Release panel on the draw page (NekoTab, from the plans launch)
        path('panel/release-teams/',
            release_views.DrawReleaseToTeamsView.as_view(),
            name='draw-release-teams'),
        path('panel/make-public/',
            release_views.DrawMakePublicView.as_view(),
            name='draw-make-public'),
        path('panel/unrelease/',
            release_views.DrawPanelUnreleaseView.as_view(),
            name='draw-panel-unrelease'),
        path('panel/motions/release/',
            release_views.PanelReleaseMotionsView.as_view(),
            name='draw-panel-motions-release'),
        path('panel/motions/unrelease/',
            release_views.PanelUnreleaseMotionsView.as_view(),
            name='draw-panel-motions-unrelease'),
        path('panel/self-checkin/',
            release_views.SelfCheckinToggleView.as_view(),
            name='draw-panel-self-checkin'),

        # Scheduling
        path('start-time/set/',
            views.SetRoundStartTimeView.as_view(),
            name='draw-start-time-set'),
    ])),

    path('round/current/display-by-venue/',
        views.AdminDrawDisplayForCurrentRoundsByVenueView.as_view(),
        name='draw-display-current-rounds-by-venue'),
    path('round/current/display-by-team/',
        views.AdminDrawDisplayForCurrentRoundsByTeamView.as_view(),
        name='draw-display-current-rounds-by-team'),

    path('sides/',
        views.SideAllocationsView.as_view(),
        name='draw-side-allocations'),
]
