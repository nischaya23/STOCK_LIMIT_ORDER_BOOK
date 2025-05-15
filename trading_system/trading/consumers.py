import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Order, Trade
from django.db.models import Q

class OrderBookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "orderbook_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def orderbook_update(self, event):
        # event['data'] contains your payload
        await self.send(text_data=json.dumps(event['data']))

