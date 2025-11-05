from django.urls import include, path

from .views import PublicSignupView

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('signup/', PublicSignupView.as_view(), name='signup'),
]
