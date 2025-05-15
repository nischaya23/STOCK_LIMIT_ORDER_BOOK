import json
from channels.generic.websocket import AsyncWebsocketConsumer

class OrderBookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            "message": "Connected to OrderBook WebSocket"
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Handle messages if client sends anything
        print("Received:", data)

    async def disconnect(self, close_code):
        print("Disconnected")
