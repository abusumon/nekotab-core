import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from donations.models import DonationTransaction
from donations.services import normalize_lemonsqueezy_payload


class Command(BaseCommand):
    help = 'Backfill donation transactions from Lemon Squeezy orders API.'

    def add_arguments(self, parser):
        parser.add_argument('--api-key', dest='api_key', default='')
        parser.add_argument('--store-id', dest='store_id', default='')
        parser.add_argument('--max-pages', dest='max_pages', type=int, default=10)

    def handle(self, *args, **options):
        api_key = options['api_key'] or getattr(settings, 'LEMON_SQUEEZY_API_KEY', '')
        store_id = options['store_id'] or getattr(settings, 'LEMON_SQUEEZY_STORE_ID', '')
        max_pages = options['max_pages']

        if not api_key:
            raise CommandError('Missing API key. Set LEMON_SQUEEZY_API_KEY or pass --api-key.')
        if not store_id:
            raise CommandError('Missing store ID. Set LEMON_SQUEEZY_STORE_ID or pass --store-id.')

        created_count = 0
        updated_count = 0

        for page_number in range(1, max_pages + 1):
            params = urlencode({
                'filter[store_id]': store_id,
                'page[number]': page_number,
                'page[size]': 100,
            })
            url = f'https://api.lemonsqueezy.com/v1/orders?{params}'

            request = Request(
                url,
                headers={
                    'Accept': 'application/vnd.api+json',
                    'Authorization': f'Bearer {api_key}',
                },
                method='GET',
            )

            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode('utf-8'))

            orders = payload.get('data') or []
            if not orders:
                break

            for order_obj in orders:
                normalized = normalize_lemonsqueezy_payload({
                    'meta': {'event_name': 'order_synced', 'test_mode': False},
                    'data': order_obj,
                })
                if not normalized:
                    continue

                _, created = DonationTransaction.objects.update_or_create(
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
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            next_link = (payload.get('links') or {}).get('next')
            if not next_link:
                break

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete. Created: {created_count}, Updated: {updated_count}'
        ))
