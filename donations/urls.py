from django.urls import path

from .views import LemonSqueezyWebhookView

app_name = 'donations'

urlpatterns = [
    path('webhooks/lemonsqueezy/', LemonSqueezyWebhookView.as_view(), name='lemonsqueezy-webhook'),
]
