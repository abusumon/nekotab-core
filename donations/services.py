import hashlib
import hmac
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import DonationTransaction


TRANSACTION_EVENT_NAMES = {
    'order_created',
    'order_refunded',
    'subscription_payment_success',
    'subscription_payment_failed',
    'subscription_payment_recovered',
    'order_synced',
}


def verify_lemonsqueezy_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not raw_body or not signature or not secret:
        return False
    digest = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def cents_to_decimal(value) -> Decimal:
    if value is None:
        return Decimal('0.00')

    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                return Decimal('0.00')
            if '.' in value:
                return Decimal(value).quantize(Decimal('0.01'))

        return (Decimal(str(value)) / Decimal('100')).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')


def decimal_from_value(value) -> Decimal:
    if value is None:
        return Decimal('0.00')
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')


def parse_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, timezone.utc)

    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None

    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.utc)
    return parsed


def _relationship_id(relationships: dict, key: str) -> str:
    data = (relationships.get(key) or {}).get('data')
    if not data:
        return ''
    if isinstance(data, list):
        if not data:
            return ''
        data = data[0]
    return str(data.get('id') or '')


def _status_for_event(event_name: str, attributes: dict) -> str:
    lowered = (event_name or '').lower()

    if attributes.get('refunded') or attributes.get('refunded_at'):
        return DonationTransaction.Status.REFUNDED
    if 'refund' in lowered:
        return DonationTransaction.Status.REFUNDED
    if 'failed' in lowered:
        return DonationTransaction.Status.FAILED
    if 'cancel' in lowered or 'expired' in lowered:
        return DonationTransaction.Status.CANCELLED
    if 'success' in lowered or 'created' in lowered or lowered == 'order_synced' or 'recovered' in lowered:
        return DonationTransaction.Status.PAID

    return DonationTransaction.Status.PENDING


def _donation_type(event_name: str, object_type: str, subscription_id: str) -> str:
    blob = f"{event_name} {object_type}".lower()
    if subscription_id or 'subscription' in blob:
        return DonationTransaction.DonationType.SUBSCRIPTION
    return DonationTransaction.DonationType.ONE_TIME


def _is_transaction_event(event_name: str, object_type: str) -> bool:
    lowered_type = (object_type or '').lower()
    if (event_name or '').lower() in TRANSACTION_EVENT_NAMES:
        return True
    return lowered_type in {'orders', 'order', 'subscription-invoices', 'subscription_invoices'}


def normalize_lemonsqueezy_payload(payload: dict):
    meta = payload.get('meta') or {}
    data = payload.get('data') or {}
    attributes = data.get('attributes') or {}
    relationships = data.get('relationships') or {}

    event_name = str(meta.get('event_name') or payload.get('event_name') or '').strip()
    object_type = str(data.get('type') or '').strip()
    object_id = str(data.get('id') or '').strip()

    if not _is_transaction_event(event_name, object_type):
        return None

    order_id = str(attributes.get('order_id') or '').strip()
    if not order_id and object_type.lower() in {'orders', 'order'}:
        order_id = object_id

    subscription_id = str(attributes.get('subscription_id') or '').strip() or _relationship_id(relationships, 'subscription')
    customer_id = str(attributes.get('customer_id') or '').strip() or _relationship_id(relationships, 'customer')

    if object_type.lower() in {'orders', 'order'} and object_id:
        external_reference = f"order:{object_id}"
    elif object_type.lower() in {'subscription-invoices', 'subscription_invoices'} and object_id:
        external_reference = f"invoice:{object_id}"
    elif order_id:
        external_reference = f"order:{order_id}"
    elif object_id:
        base = object_type.lower() or 'event'
        external_reference = f"{base}:{object_id}"
    else:
        return None

    amount = cents_to_decimal(attributes.get('total'))
    if amount == Decimal('0.00'):
        amount = cents_to_decimal(attributes.get('amount'))
    if amount == Decimal('0.00'):
        amount = cents_to_decimal(attributes.get('subtotal'))
    if amount == Decimal('0.00'):
        amount = decimal_from_value(attributes.get('total_usd'))

    refunded_amount = cents_to_decimal(attributes.get('refunded_amount'))
    if refunded_amount == Decimal('0.00') and attributes.get('refunded'):
        refunded_amount = amount

    donated_at = parse_datetime(
        attributes.get('paid_at')
        or attributes.get('created_at')
        or attributes.get('updated_at')
        or attributes.get('refunded_at')
    )

    return {
        'external_reference': external_reference,
        'event_name_last': event_name,
        'donation_type': _donation_type(event_name, object_type, subscription_id),
        'status': _status_for_event(event_name, attributes),
        'amount': amount,
        'refunded_amount': refunded_amount,
        'currency': str(attributes.get('currency') or 'USD').upper(),
        'donor_name': str(attributes.get('user_name') or attributes.get('customer_name') or '').strip(),
        'donor_email': str(attributes.get('user_email') or attributes.get('customer_email') or '').strip().lower(),
        'lemon_order_id': order_id,
        'lemon_subscription_id': subscription_id,
        'lemon_customer_id': customer_id,
        'checkout_identifier': str(attributes.get('identifier') or '').strip(),
        'product_name': str(attributes.get('product_name') or '').strip(),
        'variant_name': str(attributes.get('variant_name') or '').strip(),
        'donated_at': donated_at,
        'metadata': {
            'event_name': event_name,
            'test_mode': bool(meta.get('test_mode', False)),
            'urls': attributes.get('urls') or {},
        },
        'raw_payload': payload,
    }
