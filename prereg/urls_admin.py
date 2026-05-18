from django.urls import path

from . import views

urlpatterns = [
    # Team pre-reg dashboard
    path('', views.PreRegAdminDashboardView.as_view(), name='prereg-admin-dashboard'),
    path('settings/', views.PreRegFormSettingsView.as_view(), name='prereg-form-settings'),
    path('fields/add/', views.PreRegAddFieldView.as_view(), name='prereg-field-add'),
    path('fields/<int:field_pk>/delete/', views.PreRegDeleteFieldView.as_view(), name='prereg-field-delete'),
    path('allocate/', views.PreRegSaveAllocationsView.as_view(), name='prereg-save-allocations'),
    path('publish/', views.PreRegPublishView.as_view(), name='prereg-publish'),
    path('send-offers/', views.PreRegSendOffersView.as_view(), name='prereg-send-offers'),
    path('confirm-payment/<int:sub_pk>/', views.PreRegConfirmPaymentView.as_view(), name='prereg-confirm-payment'),
    path('send-final/<int:sub_pk>/', views.PreRegSendFinalEmailView.as_view(), name='prereg-send-final'),
    path('reject/<int:sub_pk>/', views.PreRegRejectSubmissionView.as_view(), name='prereg-reject'),
    # Adj responses
    path('adj/', views.PreRegAdjAdminView.as_view(), name='prereg-admin-adj'),
    path('adj/settings/', views.PreRegAdjFormSettingsView.as_view(), name='prereg-adj-form-settings'),
    path('adj/fields/add/', views.PreRegAdjAddFieldView.as_view(), name='prereg-adj-field-add'),
    path('adj/fields/<int:field_pk>/delete/', views.PreRegAdjDeleteFieldView.as_view(), name='prereg-adj-field-delete'),
]
