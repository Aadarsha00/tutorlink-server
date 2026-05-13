from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation
from .serializers import ConversationSerializer, MessageSerializer, SendMessageSerializer
from .services import MessageService


class ConversationQuerysetMixin:
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(Q(parent=user) | Q(teacher=user))
            .select_related("gig", "parent", "teacher")
            .prefetch_related("messages__sender")
        )


class ConversationListView(ConversationQuerysetMixin, ListAPIView):
    serializer_class = ConversationSerializer
    pagination_class = None


class ConversationDetailView(ConversationQuerysetMixin, RetrieveAPIView):
    serializer_class = ConversationSerializer


class ConversationMessagesView(ConversationQuerysetMixin, APIView):
    def get(self, request, pk):
        conversation = get_object_or_404(self.get_queryset(), pk=pk)
        messages = conversation.messages.select_related("sender").order_by("created_at")
        return Response(
            MessageSerializer(
                messages,
                many=True,
                context={"request": request},
            ).data
        )

    def post(self, request, pk):
        conversation = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = MessageService.send_message(
            conversation=conversation,
            sender=request.user,
            body=serializer.validated_data["body"],
        )
        data = MessageSerializer(message, context={"request": request}).data
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"conversation_{conversation.id}",
                {"type": "chat.message", "data": data},
            )
        return Response(data, status=status.HTTP_201_CREATED)


class ConversationReadView(ConversationQuerysetMixin, APIView):
    def post(self, request, pk):
        conversation = get_object_or_404(self.get_queryset(), pk=pk)
        result = MessageService.mark_read(conversation, request.user)
        if result["marked_count"]:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{conversation.id}",
                    {
                        "type": "messages.read",
                        "data": {
                            "conversation_id": conversation.id,
                            "reader_id": request.user.id,
                            **result,
                        },
                    },
                )
        return Response(result)


class MessagingUnreadCountView(ConversationQuerysetMixin, APIView):
    def get(self, request):
        conversations = self.get_queryset()
        unread_count = 0
        for conversation in conversations:
            unread_count += (
                conversation.messages.filter(read_at__isnull=True)
                .exclude(sender=request.user)
                .count()
            )
        return Response({"unread_count": unread_count})
