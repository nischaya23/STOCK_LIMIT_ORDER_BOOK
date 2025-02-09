import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Global variable
paused = False

class PauseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("pause_group", self.channel_name)
        await self.accept()
        await self.send(json.dumps({"paused": paused}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("pause_group", self.channel_name)

    async def receive(self, text_data):
        global paused
        data = json.loads(text_data)
        paused = data["paused"]

        # Broadcast the update to all connected users
        await self.channel_layer.group_send(
            "pause_group",
            {
                "type": "pause_update",
                "paused": paused,
            }
        )

    async def pause_update(self, event):
        await self.send(text_data=json.dumps({"paused": event["paused"]}))
