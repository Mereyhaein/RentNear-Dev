import os

from django.core.wsgi import get_wsgi_application

from rentnear.env import load_env

load_env()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rentnear.settings")

application = get_wsgi_application()
