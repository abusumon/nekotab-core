from django.urls import path
from . import views

urlpatterns = [
    path('', views.PracticeSessionListView.as_view(), name='practice-list'),
    path('new/', views.PracticeSessionCreateView.as_view(), name='practice-create'),
    path('<int:pk>/', views.PracticeSessionDetailView.as_view(), name='practice-detail'),
    path('<int:pk>/score/', views.ScoreInputView.as_view(), name='practice-score'),
    path('<int:pk>/add-room/', views.AddRoomView.as_view(), name='practice-add-room'),
    path('<int:pk>/add-participant/', views.AddParticipantView.as_view(), name='practice-add-participant'),
]
