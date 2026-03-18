from django.urls import path

from . import views

urlpatterns = [
    path('',
        views.IEPublicDashboardView.as_view(),
        name='ie-public-dashboard'),
    path('<int:event_id>/standings/',
        views.IEStandingsView.as_view(),
        name='ie-public-standings'),
    path('judge-ballot/<str:token>/',
        views.IEJudgeBallotView.as_view(),
        name='ie-judge-ballot'),
]
