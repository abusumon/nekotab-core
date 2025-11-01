#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tabbycat.settings")

    # Make repo root importable so 'tabbycat' package is found
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)