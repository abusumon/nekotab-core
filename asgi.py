import asyncio
import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ChannelNameRouter, ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path


class LimitHttpConcurrency:
    """Queue HTTP requests above a per-worker limit instead of running them all.

    Under ASGI every in-flight request gets its own thread and so its own
    Postgres connection. When a draw or results release sends a few hundred
    people to the site in the same second, two workers opened more than
    max_connections (100) and every request failed with "too many clients"
    for about a minute (2026-10-14/15/17). Excess requests now wait their turn;
    WebSockets are not limited.
    """

    def __init__(self, app, limit):
        self.app = app
        self.semaphore = asyncio.Semaphore(limit)

    async def __call__(self, scope, receive, send):
        async with self.semaphore:
            await self.app(scope, receive, send)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from actionlog.consumers import ActionLogEntryConsumer # noqa: E402 (has to come after settings)
from adjallocation.consumers import AdjudicatorAllocationWorkerConsumer, PanelEditConsumer # noqa: E402 (has to come after settings)
from chat.routing import websocket_urlpatterns as chat_ws_patterns # noqa: E402
from checkins.consumers import CheckInEventConsumer # noqa: E402 (has to come after settings)
from draw.consumers import DebateEditConsumer # noqa: E402 (has to come after settings)
from notifications.consumers import NotificationQueueConsumer # noqa: E402 (has to come after settings)
from results.consumers import BallotResultConsumer, BallotStatusConsumer # noqa: E402 (has to come after settings)
from venues.consumers import VenuesWorkerConsumer # noqa: E402 (has to come after settings)

application = ProtocolTypeRouter({

    # Django's ASGI application to handle traditional HTTP requests
    "http": LimitHttpConcurrency(get_asgi_application(), int(os.environ.get('WEB_MAX_CONCURRENT_REQUESTS') or 30)),

    # WebSocket handlers
    "websocket": AuthMiddlewareStack(
        URLRouter([
            # TournamentOverviewContainer
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/action_logs/$', ActionLogEntryConsumer.as_asgi()),
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/ballot_results/$', BallotResultConsumer.as_asgi()),
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/ballot_statuses/$', BallotStatusConsumer.as_asgi()),
            # CheckInStatusContainer
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/checkins/$', CheckInEventConsumer.as_asgi()),
            # Draw and Preformed Panel Edits
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/round/(?P<round_seq>[-\w_]+)/debates/$', DebateEditConsumer.as_asgi()),
            re_path(r'^ws/(?P<tournament_slug>[-\w_]+)/round/(?P<round_seq>[-\w_]+)/panels/$', PanelEditConsumer.as_asgi()),
            # Tournament Chat Rooms
            *chat_ws_patterns,
        ]),
    ),

    # Worker handlers (which don't need a URL/protocol)
    "channel": ChannelNameRouter({
        # Name used in runworker cmd : SyncConsumer responsible
        "notifications":  NotificationQueueConsumer.as_asgi(), # Email sending
        "adjallocation": AdjudicatorAllocationWorkerConsumer.as_asgi(),
        "venues": VenuesWorkerConsumer.as_asgi(),
    }),
})
