# routing.py
from django.urls import re_path
from trading import consumers

websocket_urlpatterns = [
    re_path(r'ws/orderbook/$', consumers.OrderBookConsumer.as_asgi()),
]

