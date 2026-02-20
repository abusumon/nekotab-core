from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('users/', views.UsersListView.as_view(), name='users'),
    path('users/export/', views.ExportUsersView.as_view(), name='export_users'),
    path('tournaments/', views.TournamentsListView.as_view(), name='tournaments'),
    path('tournaments/delete/', views.DeleteTournamentsView.as_view(), name='delete_tournaments'),
    path('db-usage/', views.DbUsageView.as_view(), name='db_usage'),
    path('db-usage/refresh/', views.RefreshDbUsageCacheView.as_view(), name='db_usage_refresh'),
    
    # API endpoints
    path('api/live-visitors/', views.LiveVisitorsAPIView.as_view(), name='api_live_visitors'),
    path('api/traffic/', views.TrafficChartAPIView.as_view(), name='api_traffic'),
]
