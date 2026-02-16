from django.urls import path
from . import views

app_name = 'motionbank'

urlpatterns = [
    # SEO-friendly page views (server-rendered shells)
    path('', views.MotionBankHomeView.as_view(), name='motionbank-home'),
    path('submit/', views.MotionSubmitView.as_view(), name='motionbank-submit'),
    path('doctor/', views.MotionDoctorView.as_view(), name='motion-doctor'),
    path('motion/<slug:slug>/', views.MotionDetailView.as_view(), name='motion-detail'),

    # API endpoints
    path('api/motions/', views.MotionEntryListAPI.as_view(), name='api-motionbank-list'),
    path('api/motions/<slug:slug>/', views.MotionEntryDetailAPI.as_view(), name='api-motionbank-detail'),
    path('api/filters/', views.MotionFiltersAPI.as_view(), name='api-motionbank-filters'),
    path('api/rate/', views.MotionRateAPI.as_view(), name='api-motionbank-rate'),
    path('api/outlines/<int:motion_id>/', views.CaseOutlineListAPI.as_view(), name='api-case-outlines'),
    path('api/outlines/<int:outline_id>/vote/', views.CaseOutlineVoteAPI.as_view(), name='api-case-outline-vote'),
    path('api/doctor/analyze/', views.MotionDoctorAnalyzeAPI.as_view(), name='api-motion-doctor'),
    path('api/doctor/feedback/', views.MotionReportFeedbackAPI.as_view(), name='api-motion-doctor-feedback'),
    path('api/practice/', views.PracticeSessionAPI.as_view(), name='api-practice-sessions'),
]
