from django.urls import path

from . import views

urlpatterns = [
    path('', views.PublicPreRegFormView.as_view(), name='prereg-team-form'),
    path('adj/', views.PublicAdjRegFormView.as_view(), name='prereg-adj-form'),
    path('success/', views.SubmissionSuccessView.as_view(), name='prereg-submission-success'),
    path('slots/', views.PublicSlotsView.as_view(), name='prereg-public-slots'),
]
