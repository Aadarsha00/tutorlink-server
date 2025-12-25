from rest_framework import serializers
from .models import Gig
from applications.models import Application


class GigListSerializer(serializers.ModelSerializer):
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Gig
        fields = [
            "id",
            "title",
            "subject",
            "grade",
            "budget_min",
            "budget_max",
            "location",
            "status",
            "created_at",
            "applications_count",
        ]

    def get_applications_count(self, obj):
        return obj.applications.count()
