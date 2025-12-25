from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""

    async def connect(self):
        """Handle WebSocket connection"""
        # Get JWT token from query string
        token = (
            self.scope["query_string"].decode().split("token=")[1]
            if "token=" in self.scope["query_string"].decode()
            else None
        )

        if not token:
            await self.close()
            return

        # Verify token and get user
        user = await self.get_user_from_token(token)

        if not user:
            await self.close()
            return

        self.user = user
        self.user_channel = f"user_{user.id}"

        # Join user's personal channel
        await self.channel_layer.group_add(self.user_channel, self.channel_name)

        await self.accept()

        # Send connection confirmation
        await self.send_json(
            {
                "type": "connection.established",
                "data": {
                    "user_id": user.id,
                    "unread_count": await self.get_unread_count(user),
                },
            }
        )

        logger.info(f"WebSocket connected for user {user.id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, "user_channel"):
            await self.channel_layer.group_discard(self.user_channel, self.channel_name)
            logger.info(f"WebSocket disconnected for user {self.user.id}")

    async def receive_json(self, content):
        """Handle messages from client"""
        message_type = content.get("type")

        if message_type == "notification.mark_read":
            notification_id = content.get("notification_id")
            if notification_id:
                success = await self.mark_notification_read(notification_id)
                await self.send_json(
                    {
                        "type": "notification.marked_read",
                        "notification_id": notification_id,
                        "success": success,
                    }
                )

        elif message_type == "ping":
            await self.send_json({"type": "pong"})

    async def notification_new(self, event):
        """Send new notification to client"""
        await self.send_json({"type": "notification.new", "data": event["data"]})

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            return User.objects.get(id=user_id, is_active=True)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None

    @database_sync_to_async
    def get_unread_count(self, user):
        """Get unread notification count"""
        from .models import Notification

        return Notification.objects.filter(user=user, is_read=False).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        from .services import NotificationService

        return NotificationService.mark_as_read(notification_id, self.user)
