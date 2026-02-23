from django.urls import include, path

from .views import ActivateAccountView, PublicSignupView

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('signup/', PublicSignupView.as_view(), name='signup'),
    path('verify/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate-account'),
]
