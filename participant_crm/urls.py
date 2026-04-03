from django.urls import path
from . import views

# No app_name — URL names are registered in the enclosing analytics namespace
# so they become analytics:participants_all, analytics:participants_debaters, etc.

urlpatterns = [
    path('', views.AllParticipantsView.as_view(), name='participants_all'),
    path('debaters/', views.DebatersView.as_view(), name='participants_debaters'),
    path('adjudicators/', views.AdjudicatorsView.as_view(), name='participants_adjudicators'),
    path('tab-directors/', views.TabDirectorsView.as_view(), name='participants_tab_directors'),
    path('export/', views.ExportParticipantsView.as_view(), name='participants_export'),
    path('add-tag/', views.AddTagView.as_view(), name='participants_add_tag'),
    path('api/recipient-preview/', views.RecipientPreviewAPIView.as_view(), name='participants_recipient_preview'),
]
