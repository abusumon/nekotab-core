import hashlib
import json
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import DonationTransaction, LemonWebhookEvent
from .services import normalize_lemonsqueezy_payload, verify_lemonsqueezy_signature

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class LemonSqueezyWebhookView(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        secret = getattr(settings, 'LEMON_SQUEEZY_WEBHOOK_SECRET', '')
        if not secret:
            logger.error('Lemon Squeezy webhook called but secret is not configured')
            return JsonResponse({'detail': 'Webhook not configured'}, status=503)

        raw_body = request.body or b''
        payload_hash = hashlib.sha256(raw_body).hexdigest()

        signature = request.headers.get('X-Signature', '')
        signature_valid = verify_lemonsqueezy_signature(raw_body, signature, secret)

        try:
            payload = json.loads(raw_body.decode('utf-8')) if raw_body else {}
        except json.JSONDecodeError:
            payload = {}

        meta = payload.get('meta') or {}
        data = payload.get('data') or {}
        event_name = str(meta.get('event_name') or payload.get('event_name') or '').strip()
        object_type = str(data.get('type') or '').strip()
        object_id = str(data.get('id') or '').strip()

        event, created = LemonWebhookEvent.objects.get_or_create(
            payload_hash=payload_hash,
            defaults={
                'event_name': event_name,
                'lemon_object_type': object_type,
                'lemon_object_id': object_id,
                'signature_valid': signature_valid,
                'payload': payload,
            },
        )

        if not created:
            return JsonResponse({'status': 'duplicate'}, status=200)

        if not signature_valid:
            event.processing_error = 'Invalid webhook signature'
            event.processed_at = timezone.now()
            event.save(update_fields=['processing_error', 'processed_at'])
            return JsonResponse({'detail': 'invalid signature'}, status=401)

        if not payload:
            event.processing_error = 'Invalid JSON payload'
            event.processed_at = timezone.now()
            event.save(update_fields=['processing_error', 'processed_at'])
            return JsonResponse({'detail': 'invalid payload'}, status=400)

        try:
            normalized = normalize_lemonsqueezy_payload(payload)
            with transaction.atomic():
                if normalized:
                    transaction_obj, _ = DonationTransaction.objects.update_or_create(
                        external_reference=normalized['external_reference'],
                        defaults={
                            'source': 'lemonsqueezy',
                            'event_name_last': normalized['event_name_last'],
                            'donation_type': normalized['donation_type'],
                            'status': normalized['status'],
                            'amount': normalized['amount'],
                            'refunded_amount': normalized['refunded_amount'],
                            'currency': normalized['currency'],
                            'donor_name': normalized['donor_name'],
                            'donor_email': normalized['donor_email'],
                            'lemon_order_id': normalized['lemon_order_id'],
                            'lemon_subscription_id': normalized['lemon_subscription_id'],
                            'lemon_customer_id': normalized['lemon_customer_id'],
                            'checkout_identifier': normalized['checkout_identifier'],
                            'product_name': normalized['product_name'],
                            'variant_name': normalized['variant_name'],
                            'donated_at': normalized['donated_at'],
                            'metadata': normalized['metadata'],
                            'raw_payload': normalized['raw_payload'],
                        },
                    )
                    event.transaction = transaction_obj

                event.processed = True
                event.processed_at = timezone.now()
                event.save(update_fields=['transaction', 'processed', 'processed_at'])
        except Exception as exc:  # pragma: no cover
            logger.exception('Failed to process Lemon Squeezy webhook')
            event.processing_error = f'Processing failed: {exc}'
            event.processed_at = timezone.now()
            event.save(update_fields=['processing_error', 'processed_at'])
            return JsonResponse({'detail': 'processing failed'}, status=500)

        return JsonResponse({'status': 'ok'}, status=200)
