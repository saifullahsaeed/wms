"""
Serializers for inventory app - stock management.
"""

from rest_framework import serializers
from .models import (
    InventoryItem,
    InventoryMovement,
    StockAdjustment,
    StockCountSession,
    StockCountLine,
    CustomFieldDefinition,
    InventoryItemCustomFieldValue,
    ProductCustomFieldValue,
)
from masterdata.models import Product, Location, Warehouse
from accounts.models import Company, User


# Inventory Item Serializers
class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for InventoryItem model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    warehouse_id = serializers.IntegerField(source="warehouse.id", read_only=True)
    warehouse_code = serializers.CharField(
        source="warehouse.code", read_only=True
    )
    product_id = serializers.IntegerField(
        source="product.id", read_only=True, allow_null=True
    )
    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    product_name = serializers.CharField(
        source="product.name", read_only=True, allow_null=True
    )
    location_id = serializers.IntegerField(
        source="location.id", read_only=True, allow_null=True
    )
    location_code = serializers.CharField(
        source="location.code", read_only=True, allow_null=True
    )
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "company_id",
            "warehouse_id",
            "warehouse_code",
            "product_id",
            "product_sku",
            "product_name",
            "location_id",
            "location_code",
            "batch",
            "expiry_date",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "warehouse_id",
            "warehouse_code",
            "product_id",
            "product_sku",
            "product_name",
            "location_id",
            "location_code",
            "available_quantity",
            "created_at",
            "updated_at",
        ]

    def get_available_quantity(self, obj):
        """Calculate available quantity."""
        return max(0, obj.quantity - obj.reserved_quantity)


class InventoryItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for inventory item lists."""

    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    location_code = serializers.CharField(
        source="location.code", read_only=True, allow_null=True
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "product_sku",
            "location_code",
            "quantity",
            "reserved_quantity",
            "is_locked",
        ]


class InventoryByProductSerializer(serializers.Serializer):
    """Serializer for inventory summary by product."""

    product_sku = serializers.CharField()
    product_name = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    total_reserved = serializers.DecimalField(max_digits=18, decimal_places=3)
    available = serializers.DecimalField(max_digits=18, decimal_places=3)


class InventoryByLocationSerializer(serializers.Serializer):
    """Serializer for inventory summary by location."""

    location_code = serializers.CharField()
    product_sku = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    reserved_quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    available = serializers.DecimalField(max_digits=18, decimal_places=3)
    batch = serializers.CharField(allow_null=True)
    expiry_date = serializers.DateField(allow_null=True)


# Inventory Movement Serializers
class InventoryMovementSerializer(serializers.ModelSerializer):
    """Serializer for InventoryMovement model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    warehouse_code = serializers.CharField(
        source="warehouse.code", read_only=True
    )
    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    location_from_code = serializers.CharField(
        source="location_from.code", read_only=True, allow_null=True
    )
    location_to_code = serializers.CharField(
        source="location_to.code", read_only=True, allow_null=True
    )
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "company_id",
            "warehouse",
            "warehouse_code",
            "product",
            "product_sku",
            "location_from",
            "location_from_code",
            "location_to",
            "location_to_code",
            "batch",
            "expiry_date",
            "movement_type",
            "quantity",
            "reference",
            "reason",
            "created_by",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "warehouse_code",
            "product_sku",
            "location_from_code",
            "location_to_code",
            "created_by_email",
            "created_at",
        ]


class InventoryMovementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for movement lists."""

    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )

    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "product_sku",
            "movement_type",
            "quantity",
            "reference",
            "created_at",
        ]


# Stock Adjustment Serializers
class StockAdjustmentSerializer(serializers.ModelSerializer):
    """Serializer for StockAdjustment model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    warehouse_code = serializers.CharField(
        source="warehouse.code", read_only=True
    )
    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    location_code = serializers.CharField(
        source="location.code", read_only=True, allow_null=True
    )
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = StockAdjustment
        fields = [
            "id",
            "company_id",
            "warehouse",
            "warehouse_code",
            "product",
            "product_sku",
            "location",
            "location_code",
            "reason",
            "description",
            "quantity_difference",
            "reference",
            "created_by",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "warehouse_code",
            "product_sku",
            "location_code",
            "created_by_email",
            "created_at",
        ]


class StockAdjustmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stock adjustments."""

    class Meta:
        model = StockAdjustment
        fields = [
            "warehouse",
            "product",
            "location",
            "reason",
            "description",
            "quantity_difference",
            "reference",
        ]


# Stock Count Session Serializers
class StockCountSessionSerializer(serializers.ModelSerializer):
    """Serializer for StockCountSession model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    warehouse_code = serializers.CharField(
        source="warehouse.code", read_only=True
    )
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, allow_null=True
    )
    lines_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockCountSession
        fields = [
            "id",
            "company_id",
            "warehouse",
            "warehouse_code",
            "name",
            "count_type",
            "status",
            "scope_description",
            "started_at",
            "completed_at",
            "created_by",
            "created_by_email",
            "lines_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "warehouse_code",
            "created_by_email",
            "lines_count",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        """Add lines count to representation."""
        ret = super().to_representation(instance)
        ret["lines_count"] = instance.lines.count()
        return ret


class StockCountSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stock count sessions."""

    class Meta:
        model = StockCountSession
        fields = [
            "warehouse",
            "name",
            "count_type",
            "scope_description",
        ]


class StockCountSessionStatusSerializer(serializers.Serializer):
    """Serializer for updating stock count session status."""

    status = serializers.ChoiceField(
        choices=StockCountSession.STATUS_CHOICES, required=True
    )


# Stock Count Line Serializers
class StockCountLineSerializer(serializers.ModelSerializer):
    """Serializer for StockCountLine model."""

    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    location_code = serializers.CharField(
        source="location.code", read_only=True, allow_null=True
    )
    counted_by_email = serializers.CharField(
        source="counted_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = StockCountLine
        fields = [
            "id",
            "session",
            "product",
            "product_sku",
            "location",
            "location_code",
            "system_quantity",
            "counted_quantity",
            "difference",
            "counted_by",
            "counted_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "product_sku",
            "location_code",
            "counted_by_email",
            "difference",
            "created_at",
            "updated_at",
        ]


class StockCountLineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stock count lines."""

    class Meta:
        model = StockCountLine
        fields = [
            "product",
            "location",
            "counted_quantity",
        ]

    def validate(self, attrs):
        """Validate and calculate system quantity and difference."""
        product = attrs.get("product")
        location = attrs.get("location")
        session = self.context.get("session")

        if not session:
            raise serializers.ValidationError("Session is required.")

        # Get system quantity from inventory
        if product and location:
            try:
                inventory_item = InventoryItem.objects.get(
                    product=product,
                    location=location,
                    warehouse=session.warehouse,
                    company=session.company,
                )
                attrs["system_quantity"] = inventory_item.quantity
            except InventoryItem.DoesNotExist:
                attrs["system_quantity"] = 0

        # Calculate difference
        counted_quantity = attrs.get("counted_quantity", 0)
        system_quantity = attrs.get("system_quantity", 0)
        attrs["difference"] = counted_quantity - system_quantity

        return attrs


# Custom Field Serializers
class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for CustomFieldDefinition model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = CustomFieldDefinition
        fields = [
            "id",
            "company_id",
            "scope",
            "name",
            "label",
            "field_type",
            "is_required",
            "is_active",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Validate field name is unique within company and scope."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company."
            )

        company = user.company
        scope = self.initial_data.get("scope")
        queryset = CustomFieldDefinition.objects.filter(
            company=company, scope=scope, name=value
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                f"A custom field with this name already exists for {scope} scope."
            )
        return value

    def create(self, validated_data):
        """Create custom field definition for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company."
            )

        validated_data["company"] = user.company
        return super().create(validated_data)


class InventoryItemCustomFieldValueSerializer(serializers.ModelSerializer):
    """Serializer for InventoryItemCustomFieldValue model."""

    field_name = serializers.CharField(source="field.name", read_only=True)
    field_label = serializers.CharField(source="field.label", read_only=True)
    field_type = serializers.CharField(source="field.field_type", read_only=True)

    class Meta:
        model = InventoryItemCustomFieldValue
        fields = [
            "id",
            "item",
            "field",
            "field_name",
            "field_label",
            "field_type",
            "value_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "field_name",
            "field_label",
            "field_type",
            "created_at",
            "updated_at",
        ]


class ProductCustomFieldValueSerializer(serializers.ModelSerializer):
    """Serializer for ProductCustomFieldValue model."""

    field_name = serializers.CharField(source="field.name", read_only=True)
    field_label = serializers.CharField(source="field.label", read_only=True)
    field_type = serializers.CharField(source="field.field_type", read_only=True)

    class Meta:
        model = ProductCustomFieldValue
        fields = [
            "id",
            "product",
            "field",
            "field_name",
            "field_label",
            "field_type",
            "value_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "field_name",
            "field_label",
            "field_type",
            "created_at",
            "updated_at",
        ]

