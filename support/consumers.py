# tickets/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("tickets", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("tickets", self.channel_name)

    async def receive(self, text_data):
        # Pas de traitement pour les messages entrants
        pass

    async def ticket_update(self, event):
        await self.send(text_data=json.dumps({
            "type": event["content"]["action"],
            "ticket": event["content"]["ticket"]
        }))
