from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # Learn hub
    path('learn/', views.LearnHubView.as_view(), name='learn-hub'),
    path('learn/<slug:slug>/', views.ArticleDetailView.as_view(), name='article-detail'),

    # Trust / Legal pages
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('disclaimer/', views.DisclaimerView.as_view(), name='disclaimer'),
]
