# asgi.py
import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# asgi.py classique Django (sans Channels)



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ton_projet.settings')

application = get_asgi_application()

