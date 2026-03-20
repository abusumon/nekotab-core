from django.urls import path

from . import views

urlpatterns = [
    path('student/session/<int:session_id>/',
        views.CongressStudentView.as_view(),
        name='congress-public-student'),
    path('standings/',
        views.CongressStandingsView.as_view(),
        name='congress-public-standings'),
]
