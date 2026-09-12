"""
Acadivo — Root URL Configuration
All app routes live in results/urls.py
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Django admin — superuser panel
    path('admin/', admin.site.urls),

    # All Acadivo routes — handled by results app
    path('', include('results.urls')),
]

# Serve media files in development (college logo, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site branding
admin.site.site_header  = 'Acadivo Administration'
admin.site.site_title   = 'Acadivo Admin'
admin.site.index_title  = 'Acadivo — Result Portal Admin'
