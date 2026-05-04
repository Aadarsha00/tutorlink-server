from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import PremiumSubscription
from .serializers import PremiumSubscriptionSerializer
from .khalti import initiate_payment, verify_payment


class PremiumSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PremiumSubscription.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=["post"])
    def initiate_payment(self, request, pk=None):
        sub = self.get_object()

        data = initiate_payment(
            amount=sub.amount,
            order_id=f"sub-{sub.id}",
            order_name="Premium Subscription",
            return_url="http://localhost:5173/payments/verify",
        )

        sub.khalti_pidx = data["pidx"]
        sub.status = "pending"
        sub.save()

        return Response(data)

    @action(detail=False, methods=["post"])
    def verify(self, request):
        data = verify_payment(request.data.get("pidx"))
        sub = PremiumSubscription.objects.get(khalti_pidx=request.data.get("pidx"))

        if data["status"] == "Completed":
            sub.status = "active"
            sub.khalti_transaction_id = data["transaction_id"]
            sub.starts_at = timezone.now()
            sub.expires_at = timezone.now() + timezone.timedelta(days=sub.duration_days)
            sub.save()

        return Response(data)
