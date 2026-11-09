#!/usr/bin/env python
import os
import sys


def main():
    from rentnear.env import load_env

    load_env()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rentnear.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Create the virtual environment and install backend/requirements.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
