"""
API views for inventory app - stock management.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from drf_spectacular.utils import extend_schema

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
from .serializers import (
    InventoryItemSerializer,
    InventoryItemListSerializer,
    InventoryByProductSerializer,
    InventoryByLocationSerializer,
    InventoryMovementSerializer,
    InventoryMovementListSerializer,
    StockAdjustmentSerializer,
    StockAdjustmentCreateSerializer,
    StockCountSessionSerializer,
    StockCountSessionCreateSerializer,
    StockCountSessionStatusSerializer,
    StockCountLineSerializer,
    StockCountLineCreateSerializer,
    CustomFieldDefinitionSerializer,
    InventoryItemCustomFieldValueSerializer,
    ProductCustomFieldValueSerializer,
)
from .services import (
    get_inventory_by_product,
    get_inventory_by_location,
)
from masterdata.models import Product, Location, Warehouse
from accounts.models import Company

User = get_user_model()


# Inventory Item Views
@extend_schema(
    tags=["Inventory - Stock Levels"],
    summary="List Inventory Items",
    description="List inventory items with filtering options.",
)
class InventoryItemListView(generics.ListAPIView):
    """List inventory items with filtering."""

    serializer_class = InventoryItemListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return inventory items for the current user's company with filtering."""
        user = self.request.user
        if not user.company:
            return InventoryItem.objects.none()

        queryset = InventoryItem.objects.filter(company=user.company).select_related(
            "product", "location", "warehouse"
        )

        # Filter by warehouse
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by product
        product_id = self.request.query_params.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Filter by location
        location_id = self.request.query_params.get("location_id")
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # Filter by batch
        batch = self.request.query_params.get("batch")
        if batch:
            queryset = queryset.filter(batch=batch)

        # Filter by has_stock (quantity > 0)
        has_stock = self.request.query_params.get("has_stock")
        if has_stock is not None:
            if has_stock.lower() == "true":
                queryset = queryset.filter(quantity__gt=0)
            else:
                queryset = queryset.filter(quantity=0)

        # Filter by is_locked
        is_locked = self.request.query_params.get("is_locked")
        if is_locked is not None:
            queryset = queryset.filter(is_locked=is_locked.lower() == "true")

        return queryset.order_by("-updated_at")


@extend_schema(
    tags=["Inventory - Stock Levels"],
    summary="Inventory Item Details",
    description="Retrieve or update an inventory item.",
)
class InventoryItemDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update an inventory item."""

    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return inventory items for the current user's company."""
        user = self.request.user
        if not user.company:
            return InventoryItem.objects.none()
        return InventoryItem.objects.filter(company=user.company).select_related(
            "product", "location", "warehouse"
        )

    def get_serializer_class(self):
        """Use full serializer for GET, limited for PATCH."""
        if self.request.method == "PATCH":
            # Only allow updating is_locked
            class LimitedSerializer(InventoryItemSerializer):
                class Meta(InventoryItemSerializer.Meta):
                    fields = ["is_locked"]

            return LimitedSerializer
        return InventoryItemSerializer


@extend_schema(
    tags=["Inventory - Stock Levels"],
    summary="Inventory by Product",
    description="Get inventory summary aggregated by product.",
)
class InventoryByProductView(generics.ListAPIView):
    """Get inventory summary by product."""

    serializer_class = InventoryByProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return inventory summary by product."""
        user = self.request.user
        if not user.company:
            return []

        warehouse_id = self.request.query_params.get("warehouse_id")
        if not warehouse_id:
            raise ValidationError({"warehouse_id": "warehouse_id is required."})

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        product_id = self.request.query_params.get("product_id")
        product = None
        if product_id:
            product = get_object_or_404(Product, id=product_id, company=user.company)

        return get_inventory_by_product(user.company, warehouse, product)


@extend_schema(
    tags=["Inventory - Stock Levels"],
    summary="Inventory by Location",
    description="Get inventory summary aggregated by location.",
)
class InventoryByLocationView(generics.ListAPIView):
    """Get inventory summary by location."""

    serializer_class = InventoryByLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return inventory summary by location."""
        user = self.request.user
        if not user.company:
            return []

        warehouse_id = self.request.query_params.get("warehouse_id")
        if not warehouse_id:
            raise ValidationError({"warehouse_id": "warehouse_id is required."})

        warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

        location_id = self.request.query_params.get("location_id")
        location = None
        if location_id:
            location = get_object_or_404(Location, id=location_id, warehouse=warehouse)

        return get_inventory_by_location(user.company, warehouse, location)


@extend_schema(
    tags=["Inventory - Stock Levels"],
    summary="Low Stock Alerts",
    description="Get products with low stock levels.",
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def low_stock_alerts(request):
    """Get low stock alerts for a warehouse."""

    user = request.user
    if not user.company:
        raise ValidationError({"error": "User is not associated with a company."})

    warehouse_id = request.query_params.get("warehouse_id")
    if not warehouse_id:
        raise ValidationError({"warehouse_id": "warehouse_id is required."})

    warehouse = get_object_or_404(Warehouse, id=warehouse_id, company=user.company)

    threshold = request.query_params.get("threshold", "0")
    try:
        threshold = Decimal(threshold)
    except (ValueError, TypeError):
        raise ValidationError({"threshold": "threshold must be a valid number."})

    # Get inventory by product
    inventory = get_inventory_by_product(user.company, warehouse)

    # Filter for low stock
    low_stock = [item for item in inventory if item["available"] <= threshold]

    return Response(low_stock, status=status.HTTP_200_OK)


# Inventory Movement Views
@extend_schema(
    tags=["Inventory - Movements"],
    summary="List Inventory Movements",
    description="List inventory movements with filtering options.",
)
class InventoryMovementListView(generics.ListAPIView):
    """List inventory movements."""

    serializer_class = InventoryMovementListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return movements for the current user's company with filtering."""
        user = self.request.user
        if not user.company:
            return InventoryMovement.objects.none()

        queryset = InventoryMovement.objects.filter(
            company=user.company
        ).select_related("product", "warehouse", "location_from", "location_to")

        # Filter by warehouse
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by product
        product_id = self.request.query_params.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Filter by movement type
        movement_type = self.request.query_params.get("movement_type")
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        # Filter by reference
        reference = self.request.query_params.get("reference")
        if reference:
            queryset = queryset.filter(reference__icontains=reference)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset.order_by("-created_at")


@extend_schema(
    tags=["Inventory - Movements"],
    summary="Inventory Movement Details",
    description="Retrieve an inventory movement.",
)
class InventoryMovementDetailView(generics.RetrieveAPIView):
    """Retrieve an inventory movement."""

    serializer_class = InventoryMovementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return movements for the current user's company."""
        user = self.request.user
        if not user.company:
            return InventoryMovement.objects.none()
        return InventoryMovement.objects.filter(company=user.company).select_related(
            "product", "warehouse", "location_from", "location_to", "created_by"
        )


# Stock Adjustment Views
def create_stock_adjustment(
    company: Company,
    warehouse: Warehouse,
    product: Product,
    location: Location,
    quantity_difference: Decimal,
    reason: str,
    description: str,
    reference: str,
    user: User,
) -> StockAdjustment:
    """Service function to create stock adjustment and movement."""

    # Create adjustment
    adjustment = StockAdjustment.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location=location,
        reason=reason,
        description=description,
        quantity_difference=quantity_difference,
        reference=reference,
        created_by=user,
    )

    # Create movement record
    movement_type = InventoryMovement.TYPE_ADJUSTMENT
    InventoryMovement.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location_from=location if quantity_difference < 0 else None,
        location_to=location if quantity_difference > 0 else None,
        movement_type=movement_type,
        quantity=abs(quantity_difference),
        reference=reference or f"ADJ-{adjustment.id}",
        reason=description or reason,
        created_by=user,
    )

    # Update inventory item
    inventory_item, created = InventoryItem.objects.get_or_create(
        company=company,
        warehouse=warehouse,
        product=product,
        location=location,
        defaults={"quantity": Decimal("0"), "reserved_quantity": Decimal("0")},
    )

    inventory_item.quantity += quantity_difference
    if inventory_item.quantity < 0 and not warehouse.allow_negative_stock:
        raise ValidationError("Negative stock not allowed for this warehouse.")
    inventory_item.save()

    return adjustment


@extend_schema(
    tags=["Inventory - Adjustments"],
    summary="List/Create Stock Adjustments",
    description="List and create stock adjustments.",
)
class StockAdjustmentListCreateView(generics.ListCreateAPIView):
    """List and create stock adjustments."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use appropriate serializer based on method."""
        if self.request.method == "POST":
            return StockAdjustmentCreateSerializer
        return StockAdjustmentSerializer

    def get_queryset(self):
        """Return adjustments for the current user's company with filtering."""
        user = self.request.user
        if not user.company:
            return StockAdjustment.objects.none()

        queryset = StockAdjustment.objects.filter(company=user.company).select_related(
            "product", "warehouse", "location", "created_by"
        )

        # Filter by warehouse
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by product
        product_id = self.request.query_params.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Filter by reason
        reason = self.request.query_params.get("reason")
        if reason:
            queryset = queryset.filter(reason=reason)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Create adjustment with movement and inventory update."""
        user = self.request.user
        if not user.company:
            raise ValidationError({"error": "User is not associated with a company."})

        validated_data = serializer.validated_data
        warehouse = validated_data["warehouse"]
        product = validated_data.get("product")
        location = validated_data.get("location")
        quantity_difference = validated_data["quantity_difference"]
        reason = validated_data.get("reason", "other")
        description = validated_data.get("description", "")
        reference = validated_data.get("reference", "")

        # Verify warehouse belongs to company
        if warehouse.company != user.company:
            raise ValidationError(
                {"warehouse": "Warehouse does not belong to your company."}
            )

        # Verify product belongs to company
        if product and product.company != user.company:
            raise ValidationError(
                {"product": "Product does not belong to your company."}
            )

        # Verify location belongs to warehouse
        if location and location.warehouse != warehouse:
            raise ValidationError(
                {"location": "Location does not belong to the specified warehouse."}
            )

        adjustment = create_stock_adjustment(
            company=user.company,
            warehouse=warehouse,
            product=product,
            location=location,
            quantity_difference=quantity_difference,
            reason=reason,
            description=description,
            reference=reference,
            user=user,
        )

        serializer.instance = adjustment


@extend_schema(
    tags=["Inventory - Adjustments"],
    summary="Stock Adjustment Details",
    description="Retrieve or delete a stock adjustment.",
)
class StockAdjustmentDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a stock adjustment."""

    serializer_class = StockAdjustmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return adjustments for the current user's company."""
        user = self.request.user
        if not user.company:
            return StockAdjustment.objects.none()
        return StockAdjustment.objects.filter(company=user.company).select_related(
            "product", "warehouse", "location", "created_by"
        )

    def destroy(self, request, *args, **kwargs):
        """Cancel adjustment by reversing the movement."""
        adjustment = self.get_object()

        # Reverse the adjustment
        reverse_quantity = -adjustment.quantity_difference

        # Update inventory
        inventory_item, created = InventoryItem.objects.get_or_create(
            company=adjustment.company,
            warehouse=adjustment.warehouse,
            product=adjustment.product,
            location=adjustment.location,
            defaults={"quantity": Decimal("0"), "reserved_quantity": Decimal("0")},
        )

        inventory_item.quantity += reverse_quantity
        inventory_item.save()

        # Create reverse movement
        InventoryMovement.objects.create(
            company=adjustment.company,
            warehouse=adjustment.warehouse,
            product=adjustment.product,
            location_from=adjustment.location if reverse_quantity < 0 else None,
            location_to=adjustment.location if reverse_quantity > 0 else None,
            movement_type=InventoryMovement.TYPE_ADJUSTMENT,
            quantity=abs(reverse_quantity),
            reference=f"REV-{adjustment.id}",
            reason=f"Reversal of adjustment {adjustment.id}",
            created_by=request.user,
        )

        adjustment.delete()

        return Response(
            {"message": "Adjustment cancelled and reversed successfully."},
            status=status.HTTP_200_OK,
        )


# Stock Count Session Views
@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="List/Create Stock Count Sessions",
    description="List and create stock count sessions.",
)
class StockCountSessionListCreateView(generics.ListCreateAPIView):
    """List and create stock count sessions."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use appropriate serializer based on method."""
        if self.request.method == "POST":
            return StockCountSessionCreateSerializer
        return StockCountSessionSerializer

    def get_queryset(self):
        """Return count sessions for the current user's company with filtering."""
        user = self.request.user
        if not user.company:
            return StockCountSession.objects.none()

        queryset = StockCountSession.objects.filter(
            company=user.company
        ).select_related("warehouse", "created_by")

        # Filter by warehouse
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by count type
        count_type = self.request.query_params.get("count_type")
        if count_type:
            queryset = queryset.filter(count_type=count_type)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Create count session for the current user's company."""
        user = self.request.user
        if not user.company:
            raise ValidationError({"error": "User is not associated with a company."})

        validated_data = serializer.validated_data
        warehouse = validated_data["warehouse"]

        # Verify warehouse belongs to company
        if warehouse.company != user.company:
            raise ValidationError(
                {"warehouse": "Warehouse does not belong to your company."}
            )

        serializer.save(company=user.company, created_by=user)


@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="Stock Count Session Details",
    description="Retrieve or update a stock count session.",
)
class StockCountSessionDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a stock count session."""

    serializer_class = StockCountSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return count sessions for the current user's company."""
        user = self.request.user
        if not user.company:
            return StockCountSession.objects.none()
        return StockCountSession.objects.filter(company=user.company).select_related(
            "warehouse", "created_by"
        )


@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="Start Stock Count Session",
    description="Start a stock count session.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def start_stock_count_session(request, pk):
    """Start a stock count session."""

    session = get_object_or_404(StockCountSession, id=pk, company=request.user.company)

    if session.status != StockCountSession.STATUS_DRAFT:
        raise ValidationError(
            {
                "error": f"Can only start sessions with status '{StockCountSession.STATUS_DRAFT}'."
            }
        )

    session.status = StockCountSession.STATUS_IN_PROGRESS
    session.started_at = timezone.now()
    session.save()

    return Response(
        StockCountSessionSerializer(session).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="Complete Stock Count Session",
    description="Complete a stock count session and create adjustments for variances.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def complete_stock_count_session(request, pk):
    """Complete a stock count session and create adjustments."""

    session = get_object_or_404(StockCountSession, id=pk, company=request.user.company)

    if session.status != StockCountSession.STATUS_IN_PROGRESS:
        raise ValidationError(
            {
                "error": f"Can only complete sessions with status '{StockCountSession.STATUS_IN_PROGRESS}'."
            }
        )

    # Process all lines with variances
    lines = session.lines.filter(difference__ne=Decimal("0"))
    adjustments_created = 0

    for line in lines:
        if line.difference != 0:
            try:
                create_stock_adjustment(
                    company=session.company,
                    warehouse=session.warehouse,
                    product=line.product,
                    location=line.location,
                    quantity_difference=line.difference,
                    reason="count",
                    description=f"Stock count variance from session {session.id}",
                    reference=f"COUNT-{session.id}",
                    user=request.user,
                )
                adjustments_created += 1
            except Exception as e:
                # Log error but continue processing
                pass

    session.status = StockCountSession.STATUS_COMPLETED
    session.completed_at = timezone.now()
    session.save()

    return Response(
        {
            "session": StockCountSessionSerializer(session).data,
            "adjustments_created": adjustments_created,
            "message": "Stock count session completed successfully.",
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="Cancel Stock Count Session",
    description="Cancel a stock count session.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cancel_stock_count_session(request, pk):
    """Cancel a stock count session."""

    session = get_object_or_404(StockCountSession, id=pk, company=request.user.company)

    if session.status == StockCountSession.STATUS_COMPLETED:
        raise ValidationError({"error": "Cannot cancel a completed session."})

    session.status = StockCountSession.STATUS_CANCELED
    session.save()

    return Response(
        {"message": "Stock count session cancelled successfully."},
        status=status.HTTP_200_OK,
    )


# Stock Count Line Views
@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="List/Create Stock Count Lines",
    description="List and create stock count lines for a session.",
)
class StockCountLineListCreateView(generics.ListCreateAPIView):
    """List and create stock count lines."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use appropriate serializer based on method."""
        if self.request.method == "POST":
            return StockCountLineCreateSerializer
        return StockCountLineSerializer

    def get_queryset(self):
        """Return count lines for the specified session."""
        session_id = self.kwargs.get("session_id")
        user = self.request.user

        if not user.company:
            return StockCountLine.objects.none()

        session = get_object_or_404(
            StockCountSession, id=session_id, company=user.company
        )

        return (
            StockCountLine.objects.filter(session=session)
            .select_related("product", "location", "counted_by")
            .order_by("product__sku", "location__code")
        )

    def get_serializer_context(self):
        """Add session to serializer context."""
        context = super().get_serializer_context()
        session_id = self.kwargs.get("session_id")
        if session_id:
            user = self.request.user
            if user.company:
                try:
                    session = StockCountSession.objects.get(
                        id=session_id, company=user.company
                    )
                    context["session"] = session
                except StockCountSession.DoesNotExist:
                    pass
        return context

    def perform_create(self, serializer):
        """Create count line with system quantity calculation."""
        session_id = self.kwargs.get("session_id")
        user = self.request.user

        session = get_object_or_404(
            StockCountSession, id=session_id, company=user.company
        )

        if session.status != StockCountSession.STATUS_IN_PROGRESS:
            raise ValidationError(
                {"error": "Can only add lines to sessions in progress."}
            )

        serializer.save(session=session, counted_by=user)


@extend_schema(
    tags=["Inventory - Stock Counts"],
    summary="Stock Count Line Details",
    description="Retrieve, update, or delete a stock count line.",
)
class StockCountLineDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a stock count line."""

    serializer_class = StockCountLineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return count lines for sessions in user's company."""
        user = self.request.user
        if not user.company:
            return StockCountLine.objects.none()

        return StockCountLine.objects.filter(
            session__company=user.company
        ).select_related("product", "location", "counted_by", "session")

    def perform_update(self, serializer):
        """Update count line and recalculate difference."""
        instance = serializer.save()

        # Recalculate difference
        instance.difference = instance.counted_quantity - instance.system_quantity
        instance.save()


# Custom Field Definition Views
@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="List/Create Custom Field Definitions",
    description="List and create custom field definitions.",
)
class CustomFieldDefinitionListCreateView(generics.ListCreateAPIView):
    """List and create custom field definitions."""

    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return field definitions for the current user's company."""
        user = self.request.user
        if not user.company:
            return CustomFieldDefinition.objects.none()

        queryset = CustomFieldDefinition.objects.filter(company=user.company)

        # Filter by scope
        scope = self.request.query_params.get("scope")
        if scope:
            queryset = queryset.filter(scope=scope)

        return queryset.order_by("scope", "order", "name")

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="Custom Field Definition Details",
    description="Retrieve, update, or delete a custom field definition.",
)
class CustomFieldDefinitionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a custom field definition."""

    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return field definitions for the current user's company."""
        user = self.request.user
        if not user.company:
            return CustomFieldDefinition.objects.none()
        return CustomFieldDefinition.objects.filter(company=user.company)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Product Custom Field Value Views
@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="List/Create Product Custom Field Values",
    description="List and create custom field values for a product.",
)
class ProductCustomFieldValueListCreateView(generics.ListCreateAPIView):
    """List and create custom field values for a product."""

    serializer_class = ProductCustomFieldValueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return custom field values for the specified product."""
        product_id = self.kwargs.get("product_id")
        user = self.request.user

        if not user.company:
            return ProductCustomFieldValue.objects.none()

        product = get_object_or_404(Product, id=product_id, company=user.company)

        return (
            ProductCustomFieldValue.objects.filter(product=product)
            .select_related("field")
            .order_by("field__order", "field__name")
        )

    def perform_create(self, serializer):
        """Set product from URL parameter."""
        product_id = self.kwargs.get("product_id")
        user = self.request.user

        product = get_object_or_404(Product, id=product_id, company=user.company)
        serializer.save(product=product)


@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="Product Custom Field Value Details",
    description="Retrieve, update, or delete a product custom field value.",
)
class ProductCustomFieldValueDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a product custom field value."""

    serializer_class = ProductCustomFieldValueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return custom field values for products in user's company."""
        user = self.request.user
        if not user.company:
            return ProductCustomFieldValue.objects.none()

        return ProductCustomFieldValue.objects.filter(
            product__company=user.company
        ).select_related("product", "field")


# Inventory Item Custom Field Value Views
@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="List/Create Inventory Item Custom Field Values",
    description="List and create custom field values for an inventory item.",
)
class InventoryItemCustomFieldValueListCreateView(generics.ListCreateAPIView):
    """List and create custom field values for an inventory item."""

    serializer_class = InventoryItemCustomFieldValueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return custom field values for the specified inventory item."""
        item_id = self.kwargs.get("item_id")
        user = self.request.user

        if not user.company:
            return InventoryItemCustomFieldValue.objects.none()

        item = get_object_or_404(InventoryItem, id=item_id, company=user.company)

        return (
            InventoryItemCustomFieldValue.objects.filter(item=item)
            .select_related("field")
            .order_by("field__order", "field__name")
        )

    def perform_create(self, serializer):
        """Set inventory item from URL parameter."""
        item_id = self.kwargs.get("item_id")
        user = self.request.user

        item = get_object_or_404(InventoryItem, id=item_id, company=user.company)
        serializer.save(item=item)


@extend_schema(
    tags=["Inventory - Custom Fields"],
    summary="Inventory Item Custom Field Value Details",
    description="Retrieve, update, or delete an inventory item custom field value.",
)
class InventoryItemCustomFieldValueDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an inventory item custom field value."""

    serializer_class = InventoryItemCustomFieldValueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return custom field values for inventory items in user's company."""
        user = self.request.user
        if not user.company:
            return InventoryItemCustomFieldValue.objects.none()

        return InventoryItemCustomFieldValue.objects.filter(
            item__company=user.company
        ).select_related("item", "field")
