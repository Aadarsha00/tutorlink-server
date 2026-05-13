from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import Conversation
from .serializers import MessageSerializer
from .services import MessageService

User = get_user_model()


class MessagingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"

        token = self.get_token()
        if not token:
            await self.close(code=4001)
            return

        self.user = await self.get_user_from_token(token)
        if not self.user:
            await self.close(code=4002)
            return

        has_access = await self.user_has_access()
        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "type": "connection.established",
                "data": {"conversation_id": int(self.conversation_id)},
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        message_type = content.get("type")

        if message_type == "message.send":
            body = content.get("body", "")
            result = await self.create_message(body)

            if result.get("error"):
                await self.send_json(
                    {
                        "type": "message.blocked",
                        "data": result,
                    }
                )
                return

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.message",
                    "data": result["message"],
                },
            )

        elif message_type == "message.read":
            result = await self.mark_read()
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "messages.read",
                    "data": {
                        "conversation_id": int(self.conversation_id),
                        "reader_id": self.user.id,
                        **result,
                    },
                },
            )
        elif message_type == "ping":
            await self.send_json({"type": "pong"})

    async def chat_message(self, event):
        await self.send_json({"type": "message.new", "data": event["data"]})

    async def messages_read(self, event):
        await self.send_json({"type": "messages.read", "data": event["data"]})

    def get_token(self):
        query_string = self.scope["query_string"].decode()
        if "token=" not in query_string:
            return None
        token_part = query_string.split("token=", 1)[1]
        return token_part.split("&", 1)[0]

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            return User.objects.get(id=access_token["user_id"], is_active=True)
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None

    @database_sync_to_async
    def user_has_access(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            is_active=True,
        ).filter(parent=self.user).exists() or Conversation.objects.filter(
            id=self.conversation_id,
            is_active=True,
        ).filter(teacher=self.user).exists()

    @database_sync_to_async
    def create_message(self, body):
        try:
            conversation = Conversation.objects.select_related(
                "gig", "parent", "teacher"
            ).get(id=self.conversation_id)
            message = MessageService.send_message(conversation, self.user, body)
            return {"message": MessageSerializer(message).data}
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                return {
                    "error": detail.get("error", "Message blocked."),
                    "reason": detail.get("reason", "blocked"),
                }
            return {"error": "Message blocked.", "reason": "blocked"}
        except Exception:
            return {"error": "Could not send message.", "reason": "server_error"}

    @database_sync_to_async
    def mark_read(self):
        conversation = Conversation.objects.get(id=self.conversation_id)
        return MessageService.mark_read(conversation, self.user)
