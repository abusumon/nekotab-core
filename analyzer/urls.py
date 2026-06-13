from django.urls import path

from . import views

urlpatterns = [
    path('', views.AnalyzeView.as_view(), name='analyze-home'),
    path('results/', views.AnalyzeResultsView.as_view(), name='analyze-results'),
]
