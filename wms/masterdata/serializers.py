"""
Serializers for masterdata app - warehouse and product management.
"""

from rest_framework import serializers
from .models import Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for Warehouse model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "code",
            "name",
            "description",
            "company_id",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "time_zone",
            "latitude",
            "longitude",
            "type",
            "is_active",
            "allow_negative_stock",
            "uses_bins",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate warehouse code is unique."""
        user = self.context["request"].user
        company = user.company

        # Check if code already exists for this company
        queryset = Warehouse.objects.filter(company=company, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A warehouse with this code already exists for your company."
            )

        return value

    def create(self, validated_data):
        """Create warehouse for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create warehouses."
            )

        validated_data["company"] = user.company
        return super().create(validated_data)
