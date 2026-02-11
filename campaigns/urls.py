from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.CampaignListView.as_view(), name='list'),
    path('create/', views.CampaignCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.CampaignDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.CampaignUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.CampaignDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/duplicate/', views.CampaignDuplicateView.as_view(), name='duplicate'),
    path('<uuid:pk>/preview/', views.CampaignPreviewView.as_view(), name='preview'),
    path('<uuid:pk>/send-test/', views.SendTestEmailView.as_view(), name='send_test'),
    path('<uuid:pk>/send/', views.SendCampaignView.as_view(), name='send'),
    path('<uuid:pk>/retry-failed/', views.RetryFailedEmailsView.as_view(), name='retry_failed'),
    path('<uuid:pk>/stats/', views.CampaignStatsAPIView.as_view(), name='stats'),
]
