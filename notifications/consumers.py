from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get JWT token from query string
            query_string = self.scope["query_string"].decode()
            logger.info(
                f"🔌 WebSocket connection attempt. Query string length: {len(query_string)}"
            )

            token = None
            if "token=" in query_string:
                # Extract token, handling potential additional parameters
                token_part = query_string.split("token=")[1]
                token = token_part.split("&")[0] if "&" in token_part else token_part
                logger.info(f"✓ Token extracted (length: {len(token)})")

            if not token:
                logger.warning("❌ WebSocket connection rejected: No token provided")
                await self.close(code=4001)
                return

            # Verify token and get user
            logger.info("🔐 Validating token...")
            user = await self.get_user_from_token(token)

            if not user:
                logger.warning(
                    "❌ WebSocket connection rejected: Invalid token or user"
                )
                await self.close(code=4002)
                return

            self.user = user
            self.user_channel = f"user_{user.id}"
            logger.info(f"✓ User authenticated: {user.id} ({user.email})")

            # Join user's personal channel
            await self.channel_layer.group_add(self.user_channel, self.channel_name)
            logger.info(f"✓ User added to channel: {self.user_channel}")

            await self.accept()
            logger.info(f"✅ WebSocket connection ACCEPTED for user {user.id}")

            # Send connection confirmation
            unread_count = await self.get_unread_count(user)
            await self.send_json(
                {
                    "type": "connection.established",
                    "data": {
                        "user_id": user.id,
                        "unread_count": unread_count,
                        "message": "Connected to notification service",
                    },
                }
            )
            logger.info(f"✓ Connection confirmation sent to user {user.id}")

        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {type(e).__name__}: {str(e)}")
            logger.exception("Full traceback:")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, "user_channel"):
                await self.channel_layer.group_discard(
                    self.user_channel, self.channel_name
                )
                if hasattr(self, "user"):
                    logger.info(
                        f"🔌 WebSocket disconnected for user {self.user.id} (code: {close_code})"
                    )
            else:
                logger.info(
                    f"🔌 WebSocket disconnected (code: {close_code}) - no user channel"
                )
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def receive_json(self, content):
        """Handle messages from client"""
        try:
            message_type = content.get("type")
            logger.debug(
                f"📨 Received message type: {message_type} from user {self.user.id}"
            )

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
                    logger.info(
                        f"✓ Notification {notification_id} marked as read: {success}"
                    )

            elif message_type == "ping":
                await self.send_json({"type": "pong"})
                logger.debug(f"🏓 Pong sent to user {self.user.id}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def notification_new(self, event):
        """Send new notification to client (called by channel layer)"""
        try:
            await self.send_json({"type": "notification.new", "data": event["data"]})
            logger.info(
                f"📬 Notification sent to user {self.user.id}: {event['data'].get('title')}"
            )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Verify JWT token and return user"""
        try:
            logger.info("🔍 Decoding JWT token...")
            # Use djangorestframework-simplejwt for token validation
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            logger.info(f"✓ Token decoded. User ID: {user_id}")

            user = User.objects.get(id=user_id, is_active=True)
            logger.info(f"✓ User found: {user.email} (ID: {user.id})")
            return user

        except InvalidToken as e:
            logger.error(f"❌ Invalid token: {e}")
            return None
        except TokenError as e:
            logger.error(f"❌ Token error: {e}")
            return None
        except User.DoesNotExist:
            logger.error(f"❌ User {user_id} does not exist or is inactive")
            return None
        except Exception as e:
            logger.error(
                f"❌ Unexpected error validating token: {type(e).__name__}: {e}"
            )
            return None

    @database_sync_to_async
    def get_unread_count(self, user):
        """Get unread notification count"""
        try:
            from .models import Notification

            count = Notification.objects.filter(user=user, is_read=False).count()
            logger.debug(f"Unread count for user {user.id}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        try:
            from .services import NotificationService

            return NotificationService.mark_as_read(notification_id, self.user)
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
