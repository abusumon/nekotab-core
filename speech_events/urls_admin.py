from django.urls import path

from . import views

urlpatterns = [
    path('',
        views.IEDashboardView.as_view(),
        name='ie-admin-dashboard'),
    path('setup/',
        views.IESetupView.as_view(),
        name='ie-admin-setup'),
    path('<int:event_id>/draw/<int:round_number>/',
        views.IERoomDrawView.as_view(),
        name='ie-admin-draw'),
    path('<int:event_id>/ballot/<int:room_id>/',
        views.IEBallotView.as_view(),
        name='ie-admin-ballot'),
    path('<int:event_id>/standings/',
        views.IEAdminStandingsView.as_view(),
        name='ie-admin-standings'),
    path('<int:event_id>/judge-links/<int:round_number>/',
        views.IEGenerateJudgeLinksView.as_view(),
        name='ie-admin-judge-links'),
]
