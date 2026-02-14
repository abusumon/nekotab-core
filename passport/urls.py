from django.urls import path
from . import views

app_name = 'passport'

urlpatterns = [
    # Page views
    path('', views.PassportDirectoryView.as_view(), name='passport-directory'),
    path('edit/', views.PassportEditView.as_view(), name='passport-edit'),
    path('dashboard/', views.PassportDashboardView.as_view(), name='passport-dashboard'),
    path('profile/<int:user_id>/', views.PassportProfileView.as_view(), name='passport-profile'),

    # API endpoints
    path('api/passports/', views.PassportListAPI.as_view(), name='api-passport-list'),
    path('api/passports/me/', views.PassportMeAPI.as_view(), name='api-passport-me'),
    path('api/passports/<int:user_id>/', views.PassportDetailAPI.as_view(), name='api-passport-detail'),
    path('api/tournaments/', views.TournamentParticipationListAPI.as_view(), name='api-passport-tournaments'),
    path('api/tournaments/<int:pk>/', views.TournamentParticipationDetailAPI.as_view(), name='api-passport-tournament-detail'),
    path('api/tournaments/<int:participation_id>/rounds/', views.RoundPerformanceListAPI.as_view(), name='api-passport-rounds'),
    path('api/tournaments/<int:participation_id>/ballots/', views.JudgeBallotListAPI.as_view(), name='api-passport-ballots'),
    path('api/partnerships/', views.PartnershipListAPI.as_view(), name='api-passport-partnerships'),
    path('api/recompute/', views.RecomputeStatsAPI.as_view(), name='api-passport-recompute'),
    path('api/leaderboard/', views.LeaderboardAPI.as_view(), name='api-leaderboard'),
]
