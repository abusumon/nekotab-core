from django.urls import path

from . import views

urlpatterns = [
    path('',
        views.CongressDashboardView.as_view(),
        name='congress-admin-dashboard'),
    path('setup/',
        views.CongressSetupView.as_view(),
        name='congress-admin-setup'),
    path('docket/',
        views.CongressDocketView.as_view(),
        name='congress-admin-docket'),
    path('chambers/',
        views.CongressChamberView.as_view(),
        name='congress-admin-chambers'),
    path('session/<int:session_id>/',
        views.CongressSessionView.as_view(),
        name='congress-admin-session'),
    path('session/<int:session_id>/scorer/',
        views.CongressScorerView.as_view(),
        name='congress-admin-scorer'),
    path('standings/',
        views.CongressStandingsView.as_view(),
        name='congress-admin-standings'),
    path('session/<int:session_id>/po/',
        views.CongressPOView.as_view(),
        name='congress-admin-po'),
]
