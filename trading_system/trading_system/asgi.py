# your_project/asgi.py
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import trading_system.routing  # Create this

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trading_system.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            trading_system.routing.websocket_urlpatterns
        )
    ),
})
