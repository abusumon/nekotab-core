import os
import logging
import sys

from split_settings.tools import optional, include


root = logging.getLogger()
root.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# ==============================================================================
# Environments
# ==============================================================================

def _env_truthy(name):
    """Check if an env var is set and truthy (non-empty, not '0'/'false'/'no')."""
    val = os.environ.get(name, '').strip().lower()
    return val != '' and val not in ('0', 'false', 'no')


base_settings = [
    'core.py',
]

if _env_truthy('GITHUB_CI'):
    base_settings.append('github.py')
    root.info('SPLIT_SETTINGS: imported github.py')
elif _env_truthy('IN_DOCKER'):
    base_settings.append('docker.py')
    root.info('SPLIT_SETTINGS: imported docker.py')
elif _env_truthy('ON_HEROKU'):
    base_settings.append('heroku.py')
    root.info('SPLIT_SETTINGS: imported heroku.py')
elif _env_truthy('ON_RENDER'):
    base_settings.append('render.py')
    root.info('SPLIT_SETTINGS: imported render.py')
else:
    base_settings.append('local.py')
    os.environ['LOCAL_SETTINGS'] = '1'  # Tell core.py not to require DJANGO_SECRET_KEY
    if _env_truthy('LOCAL_DEVELOPMENT'):
        base_settings.append('development.py')
        root.info('SPLIT_SETTINGS: imported local.py & development.py')
    else:
        root.info('SPLIT_SETTINGS: imported local.py')

include(*base_settings)
