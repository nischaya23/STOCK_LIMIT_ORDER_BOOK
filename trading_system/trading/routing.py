from django.urls import re_path
from trading.consumers import PauseConsumer

websocket_urlpatterns = [
    re_path(r'ws/pause/$', PauseConsumer.as_asgi()),
]
