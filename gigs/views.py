from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Gig
from .serializers import GigSerializer, GigListSerializer


class GigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == "parent":
            return Gig.objects.filter(parent=user).order_by("-created_at")

        elif user.role == "teacher":
            return (
                Gig.objects.filter(
                    Q(status="open") | Q(selected_teacher=user) | Q(hired_teacher=user)
                )
                .distinct()
                .order_by("-created_at")
            )

        elif user.role == "admin":
            return Gig.objects.all().order_by("-created_at")

        return Gig.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return GigListSerializer
        return GigSerializer

    def perform_create(self, serializer):
        serializer.save(parent=self.request.user)
        
