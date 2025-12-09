"""
Serializers for masterdata app - warehouse and product management.
"""

from rest_framework import serializers
from .models import (
    Warehouse,
    Product,
    ProductCategory,
    ProductBarcode,
    LocationType,
    WarehouseZone,
    Section,
    Rack,
    Location,
    UnitOfMeasure,
    Supplier,
    Customer,
    Carrier,
    ReasonCode,
)
from accounts.models import Company, User


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
        """Validate warehouse code is unique within the company."""
        user = self.context["request"].user

        # Check if user has a company
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create warehouses."
            )

        company = user.company

        # Check if code already exists for this company
        queryset = Warehouse.objects.filter(company=company, code=value)
        if self.instance:
            # Exclude current instance when updating
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


class WarehouseCodeCheckSerializer(serializers.Serializer):
    """Serializer for checking warehouse code existence."""

    warehouse_code = serializers.CharField(
        max_length=50, required=True, help_text="Warehouse code to check"
    )
    user_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="User ID (optional if authenticated)"
    )
    company_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Company ID (optional if authenticated)",
    )

    def validate(self, attrs):
        """Validate that either user_id or company_id is provided, or user is authenticated."""
        warehouse_code = attrs.get("warehouse_code")
        user_id = attrs.get("user_id")
        company_id = attrs.get("company_id")

        if not warehouse_code:
            raise serializers.ValidationError(
                {"warehouse_code": "Warehouse code is required."}
            )

        # If both user_id and company_id are provided, company_id takes precedence
        if user_id and company_id:
            attrs.pop("user_id")  # Remove user_id, use company_id

        return attrs


# Product Serializers
class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    category_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "description",
            "company_id",
            "category_id",
            "category_name",
            "status",
            "default_uom",
            "storage_uom",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "volume_cbm",
            "track_batch",
            "track_serial",
            "hazardous",
            "requires_lot_expiry",
            "storage_requirements",
            "image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "category_name",
            "created_at",
            "updated_at",
        ]

    def validate_sku(self, value):
        """Validate SKU is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create products."
            )

        company = user.company
        queryset = Product.objects.filter(company=company, sku=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists for your company."
            )
        return value

    def validate(self, attrs):
        """Validate category if provided."""
        category_id = self.initial_data.get("category_id")
        if category_id is not None:
            user = self.context["request"].user
            if user.company:
                try:
                    category = ProductCategory.objects.get(
                        id=category_id, company=user.company
                    )
                    attrs["category"] = category
                except ProductCategory.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "category_id": "Category not found or does not belong to your company."
                        }
                    )
        return attrs

    def create(self, validated_data):
        """Create product for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create products."
            )

        validated_data["company"] = user.company
        return super().create(validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists."""

    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "category_name",
            "status",
            "default_uom",
            "created_at",
        ]


class ProductCodeCheckSerializer(serializers.Serializer):
    """Serializer for checking product SKU existence."""

    sku = serializers.CharField(
        max_length=100, required=True, help_text="Product SKU to check"
    )
    company_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Company ID (optional if authenticated)",
    )


class ProductBarcodeSerializer(serializers.ModelSerializer):
    """Serializer for ProductBarcode model."""

    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = ProductBarcode
        fields = [
            "id",
            "product",
            "product_sku",
            "barcode",
            "is_primary",
            "label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "product_sku", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate barcode uniqueness per product."""
        product = attrs.get("product")
        barcode = attrs.get("barcode")

        if product and barcode:
            existing = ProductBarcode.objects.filter(product=product, barcode=barcode)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {"barcode": "This barcode already exists for this product."}
                )

        # If setting as primary, unset other primary barcodes
        if attrs.get("is_primary") and product:
            ProductBarcode.objects.filter(product=product, is_primary=True).update(
                is_primary=False
            )

        return attrs


class BarcodeLookupSerializer(serializers.Serializer):
    """Serializer for barcode lookup."""

    barcode = serializers.CharField(
        max_length=100, required=True, help_text="Barcode to lookup"
    )


# Product Category Serializers
class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for ProductCategory model with tree support."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)
    parent_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, allow_null=True
    )
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name",
            "description",
            "company_id",
            "parent_id",
            "parent_name",
            "children_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "parent_name",
            "children_count",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        """Validate category name is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create categories."
            )

        company = user.company
        queryset = ProductCategory.objects.filter(company=company, name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A category with this name already exists for your company."
            )
        return value

    def validate(self, attrs):
        """Validate parent if provided."""
        parent_id = self.initial_data.get("parent_id")
        if parent_id is not None:
            user = self.context["request"].user
            if user.company:
                try:
                    parent = ProductCategory.objects.get(
                        id=parent_id, company=user.company
                    )
                    # Prevent circular references
                    if self.instance and self.instance.id == parent_id:
                        raise serializers.ValidationError(
                            {"parent_id": "A category cannot be its own parent."}
                        )
                    attrs["parent"] = parent
                except ProductCategory.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "parent_id": "Parent category not found or does not belong to your company."
                        }
                    )
        return attrs

    def create(self, validated_data):
        """Create category for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError(
                "User must be associated with a company to create categories."
            )

        validated_data["company"] = user.company
        return super().create(validated_data)

    def to_representation(self, instance):
        """Add children count to representation."""
        ret = super().to_representation(instance)
        ret["children_count"] = instance.children.count()
        return ret


# Location Type Serializers
class LocationTypeSerializer(serializers.ModelSerializer):
    """Serializer for LocationType model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = LocationType
        fields = [
            "id",
            "name",
            "code",
            "description",
            "company_id",
            "is_pickable",
            "is_putaway_allowed",
            "is_countable",
            "temperature_zone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate code is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        queryset = LocationType.objects.filter(company=company, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A location type with this code already exists for your company."
            )
        return value

    def create(self, validated_data):
        """Create location type for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)


# Warehouse Zone Serializers
class WarehouseZoneSerializer(serializers.ModelSerializer):
    """Serializer for WarehouseZone model."""

    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)

    class Meta:
        model = WarehouseZone
        fields = [
            "id",
            "warehouse",
            "warehouse_code",
            "name",
            "description",
            "color",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "warehouse_code", "created_at", "updated_at"]

    def validate_name(self, value):
        """Validate zone name is unique within the warehouse."""
        warehouse = self.initial_data.get("warehouse")
        if not warehouse:
            return value

        queryset = WarehouseZone.objects.filter(warehouse=warehouse, name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A zone with this name already exists for this warehouse."
            )
        return value


# Section Serializers
class SectionSerializer(serializers.ModelSerializer):
    """Serializer for Section model."""

    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    zone_name = serializers.CharField(
        source="zone.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Section
        fields = [
            "id",
            "warehouse",
            "warehouse_code",
            "zone",
            "zone_name",
            "code",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "warehouse_code",
            "zone_name",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        """Validate section code is unique within the warehouse."""
        warehouse = self.initial_data.get("warehouse")
        if not warehouse:
            return value

        queryset = Section.objects.filter(warehouse=warehouse, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A section with this code already exists for this warehouse."
            )
        return value


# Rack Serializers
class RackSerializer(serializers.ModelSerializer):
    """Serializer for Rack model."""

    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    section_code = serializers.CharField(source="section.code", read_only=True)

    class Meta:
        model = Rack
        fields = [
            "id",
            "warehouse",
            "warehouse_code",
            "section",
            "section_code",
            "code",
            "description",
            "levels",
            "positions_per_level",
            "max_weight_kg",
            "max_volume_cbm",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "warehouse_code",
            "section_code",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        """Validate rack code is unique within the section."""
        section = self.initial_data.get("section")
        if not section:
            return value

        queryset = Rack.objects.filter(section=section, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A rack with this code already exists for this section."
            )
        return value


# Location Serializers
class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""

    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    section_code = serializers.CharField(
        source="section.code", read_only=True, allow_null=True
    )
    rack_code = serializers.CharField(
        source="rack.code", read_only=True, allow_null=True
    )
    location_type_name = serializers.CharField(
        source="location_type.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "warehouse",
            "warehouse_code",
            "section",
            "section_code",
            "rack",
            "rack_code",
            "location_type",
            "location_type_name",
            "code",
            "barcode",
            "description",
            "pick_sequence",
            "length_cm",
            "width_cm",
            "height_cm",
            "max_weight_kg",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "warehouse_code",
            "section_code",
            "rack_code",
            "location_type_name",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        """Validate location code is unique within the warehouse."""
        warehouse = self.initial_data.get("warehouse")
        if not warehouse:
            return value

        queryset = Location.objects.filter(warehouse=warehouse, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A location with this code already exists for this warehouse."
            )
        return value


class LocationCodeCheckSerializer(serializers.Serializer):
    """Serializer for checking location code existence."""

    location_code = serializers.CharField(
        max_length=100, required=True, help_text="Location code to check"
    )
    warehouse_id = serializers.IntegerField(required=True, help_text="Warehouse ID")


# Unit of Measure Serializers
class UnitOfMeasureSerializer(serializers.ModelSerializer):
    """Serializer for UnitOfMeasure model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = UnitOfMeasure
        fields = [
            "id",
            "name",
            "abbreviation",
            "description",
            "company_id",
            "base_unit",
            "conversion_factor",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_abbreviation(self, value):
        """Validate abbreviation is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        queryset = UnitOfMeasure.objects.filter(company=company, abbreviation=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A unit of measure with this abbreviation already exists for your company."
            )
        return value

    def create(self, validated_data):
        """Create UOM for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)


# Supplier Serializers
class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for Supplier model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "company_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate supplier code is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        queryset = Supplier.objects.filter(company=company, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A supplier with this code already exists for your company."
            )
        return value

    def create(self, validated_data):
        """Create supplier for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)


# Customer Serializers
class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "code",
            "name",
            "email",
            "phone",
            "billing_address",
            "shipping_address",
            "company_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate customer code is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        queryset = Customer.objects.filter(company=company, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A customer with this code already exists for your company."
            )
        return value

    def create(self, validated_data):
        """Create customer for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)


# Carrier Serializers
class CarrierSerializer(serializers.ModelSerializer):
    """Serializer for Carrier model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = Carrier
        fields = [
            "id",
            "name",
            "code",
            "account_number",
            "contact_email",
            "contact_phone",
            "company_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate carrier name is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        name = attrs.get("name")
        queryset = Carrier.objects.filter(company=company, name=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A carrier with this name already exists for your company."
            )
        return attrs

    def create(self, validated_data):
        """Create carrier for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)


# Reason Code Serializers
class ReasonCodeSerializer(serializers.ModelSerializer):
    """Serializer for ReasonCode model."""

    company_id = serializers.IntegerField(source="company.id", read_only=True)

    class Meta:
        model = ReasonCode
        fields = [
            "id",
            "code",
            "description",
            "category",
            "company_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate reason code is unique within the company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        company = user.company
        queryset = ReasonCode.objects.filter(company=company, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A reason code with this code already exists for your company."
            )
        return value

    def create(self, validated_data):
        """Create reason code for the current user's company."""
        user = self.context["request"].user
        if not user.company:
            raise serializers.ValidationError("User must be associated with a company.")

        validated_data["company"] = user.company
        return super().create(validated_data)
