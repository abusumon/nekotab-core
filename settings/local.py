# local.py — development overrides (loaded by split_settings)
# Nothing extra needed for local dev at the moment.
import os

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'dev-insecure-key-nekotab-local-only-do-not-deploy',
)