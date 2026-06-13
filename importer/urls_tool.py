from django.urls import path

from . import views

urlpatterns = [
    path('', views.ImportToolView.as_view(), name='import-tool'),
]
