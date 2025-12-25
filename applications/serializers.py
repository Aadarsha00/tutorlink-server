from rest_framework import serializers
from .models import Application


class ApplicationListSerializer(serializers.ModelSerializer):
    gig = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "gig",
            "status",
            "proposed_rate",
            "created_at",
            "selected_at",
            "response_deadline",
            "responded_at",
        ]

    def get_gig(self, obj):
        return {
            "id": obj.gig.id,
            "title": obj.gig.title,
            "subject": obj.gig.subject,
            "grade": obj.gig.grade,
            "budget_min": float(obj.gig.budget_min),
            "budget_max": float(obj.gig.budget_max),
            "location": obj.gig.location,
        }
