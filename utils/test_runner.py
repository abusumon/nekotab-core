"""Custom test runner that gracefully handles Postgres-only migrations
when running tests on SQLite.

Strategy: On non-PostgreSQL backends, disable all migrations and let Django
create the test database schema directly from the current model state via
`syncdb`. This avoids the 11+ legacy Postgres-only RunSQL migrations that
cannot execute on SQLite.

Production is unaffected — migrations remain authoritative on PostgreSQL.
"""

import logging

from django.test.runner import DiscoverRunner

logger = logging.getLogger(__name__)


class SQLiteSafeTestRunner(DiscoverRunner):
    """Test runner that skips migrations on SQLite and creates the schema
    directly from models."""

    def setup_test_environment(self, **kwargs):
        from django.conf import settings
        from django.db import connections

        # Only patch for non-Postgres backends
        alias = 'default'
        engine = settings.DATABASES.get(alias, {}).get('ENGINE', '')
        if 'postgresql' not in engine:
            # Disable all migrations — Django will use syncdb instead
            from django.apps import apps
            settings.MIGRATION_MODULES = {
                app.label: None for app in apps.get_app_configs()
            }
            logger.info(
                "SQLiteSafeTestRunner: disabled migrations for %s backend, "
                "schema will be created from models via syncdb.",
                engine.rsplit('.', 1)[-1],
            )

        return super().setup_test_environment(**kwargs)
