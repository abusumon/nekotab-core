import hashlib
import hmac
import json

from django.test import Client, TestCase, override_settings

from .models import DonationTransaction, LemonWebhookEvent


def _signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


@override_settings(LEMON_SQUEEZY_WEBHOOK_SECRET='test-secret')
class LemonWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_creates_transaction_from_order_created(self):
        payload = {
            'meta': {'event_name': 'order_created', 'test_mode': True},
            'data': {
                'type': 'orders',
                'id': '12345',
                'attributes': {
                    'user_name': 'Jane Donor',
                    'user_email': 'jane@example.com',
                    'currency': 'USD',
                    'total': 500,
                    'identifier': '001',
                    'created_at': '2026-05-10T00:00:00Z',
                    'product_name': 'NekoTab Support',
                    'variant_name': 'Monthly',
                },
                'relationships': {
                    'customer': {'data': {'id': 'c_1'}},
                },
            },
        }
        body = json.dumps(payload).encode('utf-8')

        response = self.client.post(
            '/donations/webhooks/lemonsqueezy/',
            data=body,
            content_type='application/json',
            HTTP_X_SIGNATURE=_signature(body, 'test-secret'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DonationTransaction.objects.count(), 1)

        tx = DonationTransaction.objects.get()
        self.assertEqual(tx.external_reference, 'order:12345')
        self.assertEqual(str(tx.amount), '5.00')
        self.assertEqual(tx.donor_email, 'jane@example.com')
        self.assertEqual(tx.status, DonationTransaction.Status.PAID)

        event = LemonWebhookEvent.objects.get()
        self.assertTrue(event.signature_valid)
        self.assertTrue(event.processed)
        self.assertEqual(event.transaction_id, tx.id)

    def test_rejects_invalid_signature(self):
        payload = {
            'meta': {'event_name': 'order_created'},
            'data': {
                'type': 'orders',
                'id': 'bad-1',
                'attributes': {'total': 200, 'currency': 'USD'},
            },
        }
        body = json.dumps(payload).encode('utf-8')

        response = self.client.post(
            '/donations/webhooks/lemonsqueezy/',
            data=body,
            content_type='application/json',
            HTTP_X_SIGNATURE='invalid',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(DonationTransaction.objects.count(), 0)
        self.assertEqual(LemonWebhookEvent.objects.count(), 1)
