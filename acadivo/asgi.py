"""
Acadivo ASGI config — for async deployment if needed
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acadivo.settings')
application = get_asgi_application()
