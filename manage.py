#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    
    # Add parent directory to path so 'tabbycat' package is importable
    import django
    from pathlib import Path
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)