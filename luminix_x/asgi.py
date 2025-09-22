"""
ASGI config for luminix_x project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import multiprocessing

multiprocessing.set_start_method("spawn", force=True)

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'luminix_x.settings')

application = get_asgi_application()
