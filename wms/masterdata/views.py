"""
API views for masterdata app - warehouse and product management.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema

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
from .serializers import (
    WarehouseSerializer,
    WarehouseCodeCheckSerializer,
    ProductSerializer,
    ProductListSerializer,
    ProductCodeCheckSerializer,
    ProductBarcodeSerializer,
    BarcodeLookupSerializer,
    ProductCategorySerializer,
    LocationTypeSerializer,
    WarehouseZoneSerializer,
    SectionSerializer,
    RackSerializer,
    LocationSerializer,
    LocationCodeCheckSerializer,
    UnitOfMeasureSerializer,
    SupplierSerializer,
    CustomerSerializer,
    CarrierSerializer,
    ReasonCodeSerializer,
)
from accounts.models import Company
from accounts.services import assign_user_to_warehouse

User = get_user_model()


@extend_schema(
    tags=["Masterdata - Warehouses"],
    summary="List/Create Warehouses",
    description="List and create warehouses for the current user's company.",
)
class WarehouseListCreateView(generics.ListCreateAPIView):
    """
    List and create warehouses for the current user's company.

    GET /api/v1/masterdata/warehouses/ - List all warehouses for company
    POST /api/v1/masterdata/warehouses/ - Create a new warehouse
    """

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return warehouses for the current user's company."""
        user = self.request.user
        if not user.company:
            return Warehouse.objects.none()
        return Warehouse.objects.filter(company=user.company).order_by("code")

    def create(self, request, *args, **kwargs):
        """Create a new warehouse and assign creator as admin."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = serializer.save()

        # Automatically assign the creator as admin for this warehouse
        user = request.user
        if user.company == warehouse.company:
            assign_user_to_warehouse(
                user=user,
                warehouse=warehouse,
                role="admin",  # Legacy role system
                is_primary=True,  # Set as primary warehouse
            )

        return Response(
            {
                "warehouse": WarehouseSerializer(warehouse).data,
                "message": "Warehouse created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Masterdata - Warehouses"],
    summary="Warehouse Details",
    description="Retrieve, update, or delete a warehouse.",
)
class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a warehouse.

    GET /api/v1/masterdata/warehouses/{id}/ - Get warehouse details
    PUT /api/v1/masterdata/warehouses/{id}/ - Update warehouse
    PATCH /api/v1/masterdata/warehouses/{id}/ - Partially update warehouse
    DELETE /api/v1/masterdata/warehouses/{id}/ - Delete warehouse
    """

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return warehouses for the current user's company."""
        user = self.request.user
        if not user.company:
            return Warehouse.objects.none()
        return Warehouse.objects.filter(company=user.company)


@extend_schema(
    tags=["Masterdata - Warehouses"],
    summary="Check Warehouse Code",
    description="Check if a warehouse code already exists for a company.",
)
@api_view(["POST", "GET"])
@permission_classes([permissions.IsAuthenticated])
def check_warehouse_code(request):
    """
    Check if a warehouse code already exists for a company.

    Works with either user_id or company_id. If authenticated and neither
    is provided, uses the current user's company.

    POST /api/v1/masterdata/warehouses/check-code/
    GET /api/v1/masterdata/warehouses/check-code/?warehouse_code=WH-001&company_id=1

    Request Body (POST):
    {
        "warehouse_code": "WH-001",
        "user_id": 1,  // Optional
        "company_id": 1  // Optional
    }

    Response:
    {
        "exists": true,
        "warehouse_code": "WH-001",
        "company_id": 1,
        "company_name": "My Company"
    }
    """
    # Handle GET request with query parameters
    if request.method == "GET":
        warehouse_code = request.query_params.get("warehouse_code")
        user_id = request.query_params.get("user_id")
        company_id = request.query_params.get("company_id")

        if not warehouse_code:
            raise ValidationError(
                {"warehouse_code": "warehouse_code query parameter is required."}
            )

        data = {
            "warehouse_code": warehouse_code,
        }
        if user_id:
            try:
                data["user_id"] = int(user_id)
            except (ValueError, TypeError):
                raise ValidationError({"user_id": "user_id must be a valid integer."})
        if company_id:
            try:
                data["company_id"] = int(company_id)
            except (ValueError, TypeError):
                raise ValidationError(
                    {"company_id": "company_id must be a valid integer."}
                )
    else:
        # Handle POST request with body
        data = request.data

    serializer = WarehouseCodeCheckSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    validated_data = serializer.validated_data
    warehouse_code = validated_data["warehouse_code"]
    user_id = validated_data.get("user_id")
    company_id = validated_data.get("company_id")

    # Determine which company to check
    company = None

    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found.")
    elif user_id:
        try:
            user = User.objects.get(id=user_id)
            if not user.company:
                raise NotFound("User is not associated with a company.")
            company = user.company
        except User.DoesNotExist:
            raise NotFound("User not found.")
    else:
        # Use authenticated user's company
        if not request.user.company:
            raise ValidationError(
                {
                    "error": "User is not associated with a company. Please provide user_id or company_id."
                }
            )
        company = request.user.company

    # Check if warehouse code exists for this company
    exists = Warehouse.objects.filter(company=company, code=warehouse_code).exists()

    return Response(
        {
            "exists": exists,
            "warehouse_code": warehouse_code,
            "company_id": company.id,
            "company_name": company.name,
        },
        status=status.HTTP_200_OK,
    )


# Product Views
@extend_schema(
    tags=["Masterdata - Products"],
    summary="List/Create Products",
    description="List and create products for the current user's company.",
)
class ProductListCreateView(generics.ListCreateAPIView):
    """List and create products."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use list serializer for GET, full serializer for POST."""
        if self.request.method == "GET":
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        """Return products for the current user's company with filtering."""
        user = self.request.user
        if not user.company:
            return Product.objects.none()

        queryset = Product.objects.filter(company=user.company).select_related(
            "category"
        )

        # Filter by category
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Search by SKU or name
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(sku__icontains=search) | Q(name__icontains=search)
            )

        return queryset.order_by("sku")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Products"],
    summary="Product Details",
    description="Retrieve, update, or delete a product.",
)
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a product."""

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return products for the current user's company."""
        user = self.request.user
        if not user.company:
            return Product.objects.none()
        return Product.objects.filter(company=user.company).select_related("category")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set status to inactive instead of deleting."""
        instance = self.get_object()
        instance.status = Product.STATUS_INACTIVE
        instance.save()
        return Response(
            {"message": "Product deactivated successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Masterdata - Products"],
    summary="Check Product SKU",
    description="Check if a product SKU already exists for a company.",
)
@api_view(["POST", "GET"])
@permission_classes([permissions.IsAuthenticated])
def check_product_sku(request):
    """Check if a product SKU already exists for a company."""

    if request.method == "GET":
        sku = request.query_params.get("sku")
        company_id = request.query_params.get("company_id")

        if not sku:
            raise ValidationError({"sku": "sku query parameter is required."})

        data = {"sku": sku}
        if company_id:
            try:
                data["company_id"] = int(company_id)
            except (ValueError, TypeError):
                raise ValidationError(
                    {"company_id": "company_id must be a valid integer."}
                )
    else:
        data = request.data

    serializer = ProductCodeCheckSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    validated_data = serializer.validated_data
    sku = validated_data["sku"]
    company_id = validated_data.get("company_id")

    # Determine which company to check
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found.")
    else:
        if not request.user.company:
            raise ValidationError(
                {
                    "error": "User is not associated with a company. Please provide company_id."
                }
            )
        company = request.user.company

    exists = Product.objects.filter(company=company, sku=sku).exists()

    return Response(
        {
            "exists": exists,
            "sku": sku,
            "company_id": company.id,
            "company_name": company.name,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=["Masterdata - Products"],
    summary="List/Create Product Barcodes",
    description="List and create barcodes for a product.",
)
class ProductBarcodeListCreateView(generics.ListCreateAPIView):
    """List and create barcodes for a product."""

    serializer_class = ProductBarcodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return barcodes for the specified product."""
        product_id = self.kwargs.get("product_id")
        user = self.request.user

        if not user.company:
            return ProductBarcode.objects.none()

        # Verify product belongs to user's company
        product = get_object_or_404(Product, id=product_id, company=user.company)

        return ProductBarcode.objects.filter(product=product).order_by(
            "-is_primary", "created_at"
        )

    def perform_create(self, serializer):
        """Set product from URL parameter."""
        product_id = self.kwargs.get("product_id")
        user = self.request.user

        product = get_object_or_404(Product, id=product_id, company=user.company)
        serializer.save(product=product)


@extend_schema(
    tags=["Masterdata - Products"],
    summary="Product Barcode Details",
    description="Retrieve or delete a product barcode.",
)
class ProductBarcodeDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a product barcode."""

    serializer_class = ProductBarcodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return barcodes for products in user's company."""
        user = self.request.user
        if not user.company:
            return ProductBarcode.objects.none()

        return ProductBarcode.objects.filter(product__company=user.company)


@extend_schema(
    tags=["Masterdata - Products"],
    summary="Lookup Product by Barcode",
    description="Find a product by its barcode.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def lookup_product_by_barcode(request):
    """Find a product by barcode."""

    serializer = BarcodeLookupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    barcode = serializer.validated_data["barcode"]
    user = request.user

    if not user.company:
        raise ValidationError({"error": "User is not associated with a company."})

    try:
        product_barcode = ProductBarcode.objects.select_related("product").get(
            barcode=barcode, product__company=user.company
        )
        product = product_barcode.product

        return Response(
            {
                "found": True,
                "barcode": barcode,
                "product": ProductSerializer(
                    product, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )
    except ProductBarcode.DoesNotExist:
        return Response(
            {
                "found": False,
                "barcode": barcode,
                "product": None,
            },
            status=status.HTTP_200_OK,
        )


# Product Category Views
@extend_schema(
    tags=["Masterdata - Products"],
    summary="List/Create Product Categories",
    description="List and create product categories for the current user's company.",
)
class ProductCategoryListCreateView(generics.ListCreateAPIView):
    """List and create product categories."""

    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return categories for the current user's company."""
        user = self.request.user
        if not user.company:
            return ProductCategory.objects.none()

        queryset = ProductCategory.objects.filter(company=user.company).select_related(
            "parent"
        )

        # Filter by parent (for tree structure)
        parent_id = self.request.query_params.get("parent_id")
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        else:
            # Default: show root categories (no parent)
            queryset = queryset.filter(parent__isnull=True)

        return queryset.order_by("name")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Products"],
    summary="Product Category Details",
    description="Retrieve, update, or delete a product category.",
)
class ProductCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a product category."""

    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return categories for the current user's company."""
        user = self.request.user
        if not user.company:
            return ProductCategory.objects.none()
        return ProductCategory.objects.filter(company=user.company).select_related(
            "parent"
        )

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        """Delete category if it has no products."""
        instance = self.get_object()
        if instance.products.exists():
            raise ValidationError(
                "Cannot delete category that has products. Please reassign or delete products first."
            )
        return super().destroy(request, *args, **kwargs)


# Location Type Views
@extend_schema(
    tags=["Masterdata - Locations"],
    summary="List/Create Location Types",
    description="List and create location types for the current user's company.",
)
class LocationTypeListCreateView(generics.ListCreateAPIView):
    """List and create location types."""

    serializer_class = LocationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return location types for the current user's company."""
        user = self.request.user
        if not user.company:
            return LocationType.objects.none()
        return LocationType.objects.filter(company=user.company).order_by("code")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Location Type Details",
    description="Retrieve, update, or delete a location type.",
)
class LocationTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a location type."""

    serializer_class = LocationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return location types for the current user's company."""
        user = self.request.user
        if not user.company:
            return LocationType.objects.none()
        return LocationType.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Warehouse Zone Views (nested under warehouse)
@extend_schema(
    tags=["Masterdata - Locations"],
    summary="List/Create Warehouse Zones",
    description="List and create zones for a warehouse.",
)
class WarehouseZoneListCreateView(generics.ListCreateAPIView):
    """List and create zones for a warehouse."""

    serializer_class = WarehouseZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return zones for the specified warehouse."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        if not user.company:
            return WarehouseZone.objects.none()

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        return WarehouseZone.objects.filter(warehouse=warehouse).order_by("name")

    def perform_create(self, serializer):
        """Set warehouse from URL parameter."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)
        serializer.save(warehouse=warehouse)


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Warehouse Zone Details",
    description="Retrieve, update, or delete a warehouse zone.",
)
class WarehouseZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a warehouse zone."""

    serializer_class = WarehouseZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return zones for warehouses in user's company."""
        user = self.request.user
        if not user.company:
            return WarehouseZone.objects.none()

        return WarehouseZone.objects.filter(warehouse__company=user.company)


# Section Views (nested under warehouse)
@extend_schema(
    tags=["Masterdata - Locations"],
    summary="List/Create Sections",
    description="List and create sections for a warehouse.",
)
class SectionListCreateView(generics.ListCreateAPIView):
    """List and create sections for a warehouse."""

    serializer_class = SectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return sections for the specified warehouse."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        if not user.company:
            return Section.objects.none()

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        return (
            Section.objects.filter(warehouse=warehouse)
            .select_related("zone")
            .order_by("code")
        )

    def perform_create(self, serializer):
        """Set warehouse from URL parameter."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)
        serializer.save(warehouse=warehouse)


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Section Details",
    description="Retrieve, update, or delete a section.",
)
class SectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a section."""

    serializer_class = SectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return sections for warehouses in user's company."""
        user = self.request.user
        if not user.company:
            return Section.objects.none()

        return Section.objects.filter(warehouse__company=user.company)


# Rack Views (nested under warehouse)
@extend_schema(
    tags=["Masterdata - Locations"],
    summary="List/Create Racks",
    description="List and create racks for a warehouse.",
)
class RackListCreateView(generics.ListCreateAPIView):
    """List and create racks for a warehouse."""

    serializer_class = RackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return racks for the specified warehouse."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        if not user.company:
            return Rack.objects.none()

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        return (
            Rack.objects.filter(warehouse=warehouse)
            .select_related("section")
            .order_by("code")
        )

    def perform_create(self, serializer):
        """Set warehouse from URL parameter."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)
        serializer.save(warehouse=warehouse)


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Rack Details",
    description="Retrieve, update, or delete a rack.",
)
class RackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a rack."""

    serializer_class = RackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return racks for warehouses in user's company."""
        user = self.request.user
        if not user.company:
            return Rack.objects.none()

        return Rack.objects.filter(warehouse__company=user.company)


# Location Views (nested under warehouse)
@extend_schema(
    tags=["Masterdata - Locations"],
    summary="List/Create Locations",
    description="List and create locations (bins) for a warehouse.",
)
class LocationListCreateView(generics.ListCreateAPIView):
    """List and create locations for a warehouse."""

    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return locations for the specified warehouse with filtering."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        if not user.company:
            return Location.objects.none()

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        queryset = Location.objects.filter(warehouse=warehouse).select_related(
            "section", "rack", "location_type"
        )

        # Filter by zone
        zone_id = self.request.query_params.get("zone_id")
        if zone_id:
            queryset = queryset.filter(section__zone_id=zone_id)

        # Filter by section
        section_id = self.request.query_params.get("section_id")
        if section_id:
            queryset = queryset.filter(section_id=section_id)

        # Filter by rack
        rack_id = self.request.query_params.get("rack_id")
        if rack_id:
            queryset = queryset.filter(rack_id=rack_id)

        # Filter by location type
        location_type_id = self.request.query_params.get("location_type_id")
        if location_type_id:
            queryset = queryset.filter(location_type_id=location_type_id)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("code")

    def perform_create(self, serializer):
        """Set warehouse from URL parameter."""
        warehouse_id = self.kwargs.get("warehouse_id")
        user = self.request.user

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)
        serializer.save(warehouse=warehouse)


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Location Details",
    description="Retrieve, update, or delete a location.",
)
class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a location."""

    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return locations for warehouses in user's company."""
        user = self.request.user
        if not user.company:
            return Location.objects.none()

        return Location.objects.filter(warehouse__company=user.company).select_related(
            "section", "rack", "location_type"
        )


@extend_schema(
    tags=["Masterdata - Locations"],
    summary="Check Location Code",
    description="Check if a location code already exists for a warehouse.",
)
@api_view(["POST", "GET"])
@permission_classes([permissions.IsAuthenticated])
def check_location_code(request, warehouse_id):
    """Check if a location code already exists for a warehouse."""

    user = request.user
    if not user.company:
        raise ValidationError({"error": "User is not associated with a company."})

    warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

    if request.method == "GET":
        location_code = request.query_params.get("location_code")
        if not location_code:
            raise ValidationError(
                {"location_code": "location_code query parameter is required."}
            )
        data = {"location_code": location_code, "warehouse_id": warehouse_id}
    else:
        data = request.data
        data["warehouse_id"] = warehouse_id

    serializer = LocationCodeCheckSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    location_code = serializer.validated_data["location_code"]
    exists = Location.objects.filter(warehouse=warehouse, code=location_code).exists()

    return Response(
        {
            "exists": exists,
            "location_code": location_code,
            "warehouse_id": warehouse.id,
            "warehouse_code": warehouse.code,
        },
        status=status.HTTP_200_OK,
    )


# Unit of Measure Views
@extend_schema(
    tags=["Masterdata - UOM"],
    summary="List/Create Units of Measure",
    description="List and create units of measure for the current user's company.",
)
class UnitOfMeasureListCreateView(generics.ListCreateAPIView):
    """List and create units of measure."""

    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return UOMs for the current user's company."""
        user = self.request.user
        if not user.company:
            return UnitOfMeasure.objects.none()
        return UnitOfMeasure.objects.filter(company=user.company).order_by(
            "abbreviation"
        )

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - UOM"],
    summary="Unit of Measure Details",
    description="Retrieve, update, or delete a unit of measure.",
)
class UnitOfMeasureDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a unit of measure."""

    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return UOMs for the current user's company."""
        user = self.request.user
        if not user.company:
            return UnitOfMeasure.objects.none()
        return UnitOfMeasure.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Supplier Views
@extend_schema(
    tags=["Masterdata - Partners"],
    summary="List/Create Suppliers",
    description="List and create suppliers for the current user's company.",
)
class SupplierListCreateView(generics.ListCreateAPIView):
    """List and create suppliers."""

    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return suppliers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Supplier.objects.none()

        queryset = Supplier.objects.filter(company=user.company)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("code")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Partners"],
    summary="Supplier Details",
    description="Retrieve, update, or delete a supplier.",
)
class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a supplier."""

    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return suppliers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Supplier.objects.none()
        return Supplier.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active to False."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {"message": "Supplier deactivated successfully."},
            status=status.HTTP_200_OK,
        )


# Customer Views
@extend_schema(
    tags=["Masterdata - Partners"],
    summary="List/Create Customers",
    description="List and create customers for the current user's company.",
)
class CustomerListCreateView(generics.ListCreateAPIView):
    """List and create customers."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return customers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Customer.objects.none()

        queryset = Customer.objects.filter(company=user.company)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("code")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Partners"],
    summary="Customer Details",
    description="Retrieve, update, or delete a customer.",
)
class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a customer."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return customers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Customer.objects.none()
        return Customer.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active to False."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {"message": "Customer deactivated successfully."},
            status=status.HTTP_200_OK,
        )


# Carrier Views
@extend_schema(
    tags=["Masterdata - Partners"],
    summary="List/Create Carriers",
    description="List and create carriers for the current user's company.",
)
class CarrierListCreateView(generics.ListCreateAPIView):
    """List and create carriers."""

    serializer_class = CarrierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return carriers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Carrier.objects.none()

        queryset = Carrier.objects.filter(company=user.company)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("name")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Partners"],
    summary="Carrier Details",
    description="Retrieve, update, or delete a carrier.",
)
class CarrierDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a carrier."""

    serializer_class = CarrierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return carriers for the current user's company."""
        user = self.request.user
        if not user.company:
            return Carrier.objects.none()
        return Carrier.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active to False."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {"message": "Carrier deactivated successfully."},
            status=status.HTTP_200_OK,
        )


# Reason Code Views
@extend_schema(
    tags=["Masterdata - Configuration"],
    summary="List/Create Reason Codes",
    description="List and create reason codes for the current user's company.",
)
class ReasonCodeListCreateView(generics.ListCreateAPIView):
    """List and create reason codes."""

    serializer_class = ReasonCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return reason codes for the current user's company."""
        user = self.request.user
        if not user.company:
            return ReasonCode.objects.none()

        queryset = ReasonCode.objects.filter(company=user.company)

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        return queryset.order_by("code")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Masterdata - Configuration"],
    summary="Reason Code Details",
    description="Retrieve, update, or delete a reason code.",
)
class ReasonCodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a reason code."""

    serializer_class = ReasonCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return reason codes for the current user's company."""
        user = self.request.user
        if not user.company:
            return ReasonCode.objects.none()
        return ReasonCode.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
