#!/usr/bin/env python
"""
Acadivo — Django management utility
Usage:
  python manage.py runserver        — start dev server
  python manage.py makemigrations  — create DB migrations
  python manage.py migrate         — apply migrations
  python manage.py createsuperuser — create admin account
  python manage.py loaddata results/fixtures/subjects.json — load NEP subjects
"""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acadivo.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed:\n"
            "  pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
