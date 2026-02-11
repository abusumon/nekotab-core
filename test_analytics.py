#!/usr/bin/env python
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from analytics.views import DashboardView
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()
u = User.objects.filter(is_superuser=True).first()
print('User:', u)

factory = RequestFactory()
request = factory.get('/analytics/')
request.user = u

# Add session
from django.contrib.sessions.backends.db import SessionStore
request.session = SessionStore()

view = DashboardView()
view.request = request
view.kwargs = {}
view.args = ()

try:
    ctx = view.get_context_data()
    print('SUCCESS! Context keys:', list(ctx.keys()))
except Exception as e:
    import traceback
    print('ERROR:', type(e).__name__)
    traceback.print_exc()

# Also try rendering the template
print('\n--- Testing template render ---')
try:
    from django.template.loader import get_template
    t = get_template('analytics/dashboard.html')
    print('Template loaded OK')
    result = t.render(ctx, request)
    print('Template rendered OK, length:', len(result))
except Exception as e:
    import traceback
    print('TEMPLATE ERROR:', type(e).__name__)
    traceback.print_exc()
