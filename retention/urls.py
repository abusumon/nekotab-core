from django.urls import path

from . import views

app_name = 'retention'

urlpatterns = [
    path(
        'admin/retention/download/<int:log_id>/',
        views.download_archive,
        name='download-archive',
    ),
]
